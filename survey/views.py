import json
import requests
from datetime import date

# from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers import serialize
from django.db import transaction, IntegrityError
from django.db.models import Count
from django.db.models.functions import Cast, TruncMonth
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from docutils.nodes import status
from rest_framework import status
from rest_framework.response import Response as Res
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import *
from .serializer import *
from authApp.serializer import *


# api
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_questionnaire_api(request):
    quest = Facility_Questionnaire.objects.filter(facility_id=request.user.facility.id)
    list = []
    for i in quest:
        queryset = Questionnaire.objects.filter(id=i.questionnaire.id)
        serializer = QuestionnaireSerializer(queryset, many=True)
        list.append(serializer.data[0])
    print(list)
    return Res({"data": list}, status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_questionnaire_api(request):
    quest = Facility_Questionnaire.objects.filter(facility_id=request.user.facility.id)

    queryset = Questionnaire.objects.filter(id__in=quest.values_list('questionnaire_id', flat=True), is_active=True,
                                            active_till__gte=date.today())
    serializer = QuestionnaireSerializer(queryset, many=True)
    return Res({"data": serializer.data}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def all_question_api(request):
    quest = Question.objects.filter(questionnaire_id=request.data['questionnaire_id'])
    serializer = QuestionSerializer(quest, many=True)

    return Res({"data": serializer.data}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def list_question_api(request):
    quest = Answer.objects.filter(question_id=request.data['question_id'])
    serializer = QuestionResponseSerializer(quest, many=True)

    return Res({"data": serializer.data}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_consent(request):
    check = check_ccc(request.data['ccc_number'])
    if not check:
        return Res({'error': False, 'message': 'ccc number doesnt exist'})
    if check['f_name'] != request.data['first_name']:
        return Res({'error': False, 'message': 'client verification failed'})
        
    quest = Question.objects.filter(questionnaire_id=request.data['questionnaire_id'])[:1]
    a_id = 0
    for q in quest:
        a_id =q.id

    consent = Patient_Consent.objects.create(questionnaire_id=request.data['questionnaire_id'],
                                             ccc_number=request.data['ccc_number'])
    consent.save()
    session = Started_Questionnaire.objects.create(questionnaire_id=request.data['questionnaire_id'],
                                                   started_by=request.user,
                                                   ccc_number=request.data['ccc_number'],
                                                   firstname=request.data['first_name'])
    session.save()
    return JsonResponse({
        'link': 'http://psurvey-api.mhealthkenya.co.ke/api/questions/answer/{}'.format(a_id),
        'session': session.pk
    })
    # return Res({"Question": serializer.data, "Ans": ser.data, "session_id": session.pk}, status.HTTP_200_OK)


def check_ccc(value):
    user = {
        "ccc_number": value
    }

    url = "http://ushaurinode.mhealthkenya.org/api/mlab/get/one/client"
    headers = {
        'content-type': "application/json",
        'Accept': 'application/json'
    }
    response = requests.post(url, data=user, json=headers)
    try:
        return response.json()["clients"][0]
    except IndexError:
        return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def start_questionnaire_new(request, q_id):
    quest = Question.objects.get(id=q_id)
    serializer = QuestionSerializer(quest)
    queryset = Answer.objects.filter(question_id=quest)
    ser = AnswerSerializer(queryset, many=True)

    return Res({"Question": serializer.data, "Ans": ser.data}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def answer_question(request):
    q = Question.objects.get(id=request.data['question'])

    if q.question_type == 3:
        a = request.data.copy()
        trans_one = transaction.savepoint()
        b = a['answer'].split(',')

        for i in b:

            a.update({'answer': i})
            serializer = ResponseSerializer(data=a)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
            else:
                transaction.savepoint_rollback(trans_one)
                return Res({'success': False, 'error': 'Unknown error, try again'}, status=status.HTTP_400_BAD_REQUEST)

        q = Question.objects.get(id=serializer.data['question'])
        quest = Questionnaire.objects.get(id=q.questionnaire_id)
        questions = Question.objects.filter(questionnaire=quest)

        foo = q
        previous = next_ = None
        l = len(questions)
        for index, obj in enumerate(questions):
            if obj == foo:
                if index > 0:
                    previous = questions[index - 1]
                if index < (l - 1):
                    next_ = questions[index + 1]
                    return JsonResponse({
                        'link': 'http://psurvey-api.mhealthkenya.co.ke/api/questions/answer/{}'.format(next_.id),
                        "session_id": serializer.data['session']
                    })

                elif next_ == None:
                    end = End_Questionnaire.objects.create(questionnaire=quest, session_id=serializer.data['session'])
                    end.save()
                    return Res({
                        "success": True,
                        "Message": "Questionnaire complete, Thank You👌!"
                    }, status.HTTP_200_OK)
        return Res({'success': False, 'error': 'Unknown error, try again'}, status=status.HTTP_400_BAD_REQUEST)

    else:
        serializer = ResponseSerializer(data=request.data)
        print(serializer.is_valid(raise_exception=True))
        try:
            if serializer.is_valid():
                data = check_answer_algo(serializer)
            else:
                return Res({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Res(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return data


def check_answer_algo(ser):
    ser.save()
    q = Question.objects.get(id=ser.data['question'])
    quest = Questionnaire.objects.get(id=q.questionnaire_id)
    questions = Question.objects.filter(questionnaire=quest)

    foo = q
    previous = next_ = None
    l = len(questions)
    for index, obj in enumerate(questions):
        if obj == foo:
            if index > 0:
                previous = questions[index - 1]
            if index < (l - 1):
                next_ = questions[index + 1]
                serializer = QuestionSerializer(next_)
                queryset = Answer.objects.filter(question=next_)
                ans_ser = AnswerSerializer(queryset, many=True)
                return JsonResponse({
                    'link': 'http://psurvey-api.mhealthkenya.co.ke/api/questions/answer/{}'.format(next_.id),
                    "session_id": ser.data['session']
                })

            elif next_ == None:
                end = End_Questionnaire.objects.create(questionnaire=quest, session_id=ser.data['session'])
                end.save()
                return Res({
                    "success": True,
                    "Message": "Questionnaire complete, Thank You👌!"
                }, status.HTTP_200_OK)
    return Res({'success': False, 'error': 'Unknown error, try again'}, status=status.HTTP_400_BAD_REQUEST)


# web
def get_fac(request):
    if request.method == "POST":
        if request.user.access_level.id == 3:
            county_list = request.POST.getlist('county_list[]')
            print(request.POST)
            fac = Facility.objects.filter(county__in=county_list)

            serialized = serialize('json', fac)
            obj_list = json.loads(serialized)
        elif request.user.access_level.id == 2:
            county_list = request.POST.getlist('county_list[]')
            fac = Partner_Facility.objects.filter(
                partner__in=Partner_User.objects.filter(user=request.user).values_list('name', flat=True))
            fac = Facility.objects.filter(id__in=fac.values_list('facility_id', flat=True), county__in=county_list)

            serialized = serialize('json', fac)
            obj_list = json.loads(serialized)

        return HttpResponse(json.dumps(obj_list), content_type="application/json")


@login_required
def index(request):
    user = request.user
    if user.access_level.id == 3:
        fac = Facility.objects.all().order_by('county', 'sub_county', 'name')
        quest = Questionnaire.objects.all()
        aq = Questionnaire.objects.filter(is_active=True, active_till__gte=date.today())
        resp = End_Questionnaire.objects.filter()
        queryset = Facility.objects.all().distinct('county')
        context = {
            'u': user,
            'fac': fac,
            'quest': quest,
            'aq': aq,
            'resp': resp,
            'county': queryset,
        }
        return render(request, 'survey/dashboard.html', context)
    elif user.access_level.id == 2:
        fac = Facility.objects.filter(id__in=Partner_Facility.objects.filter(
            partner__in=Partner_User.objects.filter(user=user).values_list('name', flat=True)).values_list('facility_id', flat=True)).order_by('county', 'sub_county', 'name')

        quest = Facility_Questionnaire.objects.filter(facility_id__in=fac.values_list('id', flat=True)
                                                      ).values_list('questionnaire').distinct()
        aq = Facility_Questionnaire.objects.filter(facility_id__in=fac.values_list('id', flat=True),
                                                   questionnaire__is_active=True,
                                                   questionnaire__active_till__gte=date.today()
                                                   ).values_list('questionnaire').distinct()

        resp = End_Questionnaire.objects.filter(questionnaire__in=quest)
        context = {
            'u': user,
            'fac': fac,
            'quest': quest,
            'aq': aq,
            'resp': resp,
        }
        return render(request, 'survey/dashboard.html', context)


def resp_chart(request):
    start = request.POST.get('start_date')
    end = request.POST.get('end_date')
    facilities = request.POST.getlist('fac[]', '')


    labels = []
    data = []
    if request.user.access_level.id == 3:
        if facilities == '':
            facilities = Facility.objects.values_list('id', flat=True)
        st = Started_Questionnaire.objects.filter(started_by__facility_id__in=facilities)
        queryset = Response.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            session__in=st
        ).values('created_at').annotate(count=Count('created_at')).order_by('created_at')

    if request.user.access_level.id == 2:
        if facilities == '':
            facilities = Facility.objects.filter(id__in=Partner_Facility.objects.filter(
                partner__in=Partner_User.objects.filter(user=request.user).values_list('name', flat=True)).values_list(
                'facility_id', flat=True))
        st = Started_Questionnaire.objects.filter(started_by__facility_id__in=facilities)

        queryset = Response.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            session__in=st
        ).values('created_at').annotate(count=Count('created_at')).order_by('created_at')

    for entry in queryset:
        labels.append(entry['created_at'])
        data.append(entry['count'])


    return JsonResponse(data={
        'labels': labels,
        'data': data,
    })


def trend_chart(request):
    start = request.POST.get('start_date')
    end = request.POST.get('end_date')
    facilities = request.POST.getlist('fac[]', '')

    labels = []
    data = []
    if request.user.access_level.id == 3:
        if facilities == '':
            facilities = Facility.objects.values_list('id', flat=True)
        st = Started_Questionnaire.objects.filter(started_by__facility_id__in=facilities)
        re = Response.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            session__in=st
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(c=Count('month')).values(
            'month', 'c').order_by('month')


    if request.user.access_level.id == 2:
        if facilities == '':
            facilities = Facility.objects.filter(id__in=Partner_Facility.objects.filter(
                partner__in=Partner_User.objects.filter(user=request.user).values_list('name', flat=True)).values_list(
                'facility_id', flat=True))
        st = Started_Questionnaire.objects.filter(started_by__facility_id__in=facilities)

        re = Response.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            session__in=st,
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(c=Count('month')).values('month', 'c').order_by('month')

    for entry in re:
        labels.append(entry['month'].strftime('%B') + '-' + entry['month'].strftime('%y'))
        data.append(entry['c'])

    return JsonResponse(data={
        'labels': labels,
        'data': data,
    })


@login_required
def new_questionnaire(request):
    user = request.user
    u = user
    if request.method == 'POST':
        name = request.POST.get('title')
        facility = request.POST.getlist('facility')
        desc = request.POST.get('description')
        dateTill = request.POST.get('date-till')
        isActive = request.POST.get('isActive')

        if isActive == "inactive":
            isActive = False
        else:
            isActive = True
        create_quest = Questionnaire.objects.create(name=name, is_active=isActive, description=desc,
                                                    active_till=dateTill, created_by=request.user)
        create_quest.save()
        trans_one = transaction.savepoint()
        q_id = create_quest.pk
        print(q_id)

        if q_id:
            try:
                for f in facility:
                    fac_save = Facility_Questionnaire.objects.create(facility_id=f, questionnaire_id=q_id)
                    fac_save.save()
            except IntegrityError:
                transaction.savepoint_rollback(trans_one)
                return HttpResponse("error")

    if user.access_level.id == 3:
        facilities = Facility.objects.all().order_by('county', 'sub_county', 'name')
        queryset = Facility.objects.all().distinct('county')
        context = {
            'u': u,
            'county': queryset,
            'fac': facilities,
        }
        return render(request, 'survey/new_questionnaire.html', context)
    elif user.access_level.id == 2:
        fac = Partner_Facility.objects.filter(
            partner__in=Partner_User.objects.filter(user=user).values_list('name', flat=True))
        facilities = Facility.objects.filter(id__in=fac.values_list('facility_id', flat=True)).order_by('county', 'sub_county', 'name')
        queryset = Facility.objects.filter(id__in=fac.values_list('facility_id', flat=True)).distinct('county')
        context = {
            'u': u,
            'fac': facilities,
            'county': queryset,
        }
        return render(request, 'survey/new_questionnaire.html', context)


@login_required
def edit_questionnaire(request, q_id):
    user = request.user
    u = user
    if request.method == 'POST':
        name = request.POST.get('title')
        facility = request.POST.getlist('facility')
        desc = request.POST.get('description')
        dateTill = request.POST.get('date-till')
        isActive = request.POST.get('isActive')

        if isActive == "inactive":
            isActive = False
        else:
            isActive = True

        trans_one = transaction.savepoint()

        create_quest = Questionnaire.objects.get(id=q_id)
        create_quest.name = name
        create_quest.is_active = isActive
        create_quest.description = desc
        create_quest.active_till = dateTill

        create_quest.save()

        if q_id:
            try:
                fac = Facility_Questionnaire.objects.filter(questionnaire_id=q_id)
                fac_list = []
                for fi in fac:
                    fac_list.append(str(fi.facility_id))
                print(facility)
                for f in fac_list:
                    fac_rem = Facility_Questionnaire.objects.filter(facility_id=f, questionnaire_id=q_id)
                    fac_rem.delete()

                for f in facility:
                    fac_save = Facility_Questionnaire.objects.create(facility_id=f, questionnaire_id=q_id)
                    fac_save.save()
            except IntegrityError:
                transaction.savepoint_rollback(trans_one)
                return HttpResponse("error")

    if user.access_level.id == 3:
        question = Questionnaire.objects.get(id=q_id)
        selected = Facility_Questionnaire.objects.filter(questionnaire_id=q_id)
        facilities = Facility.objects.all().exclude(id__in=selected.values_list('facility_id', flat=True)).order_by('county', 'sub_county', 'name')
        s = Facility.objects.all().filter(id__in=selected.values_list('facility_id', flat=True))

        context = {
            'u': u,
            'fac': facilities,
            'q': question,
            'fac_sel': s,
        }
        return render(request, 'survey/edit_questionnaire.html', context)
    if user.access_level.id == 2:
        fac = Partner_Facility.objects.filter(
            partner__in=Partner_User.objects.filter(user=user).values_list('name', flat=True))
        selected = Facility_Questionnaire.objects.filter(questionnaire_id=q_id)
        try:
            question = Questionnaire.objects.get(id=q_id)
        except Questionnaire.DoesNotExist:
            raise Http404('Questionnaire Does not exist')

        if question.created_by.access_level.id == 3:
            raise PermissionDenied
        facilities = Facility.objects.filter(id__in=fac.values_list('facility_id', flat=True)
                                             ).exclude(id__in=selected.values_list('facility_id', flat=True)).order_by('county', 'sub_county', 'name')
        s = Facility.objects.all().filter(id__in=selected.values_list('facility_id', flat=True)).order_by('county', 'sub_county', 'name')

        context = {
            'u': u,
            'fac': facilities,
            'q': question,
            'fac_sel': s,
        }
        return render(request, 'survey/edit_questionnaire.html', context)


@login_required
def questionnaire(request):
    user = request.user
    u = user
    if request.method == "POST":
        print(request.POST)
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        if user.access_level.id == 3:
            quest = Questionnaire.objects.filter(created_at__gte=start, created_at__lte=end).order_by('-created_at')
            count = Questionnaire.objects.filter(created_at__gte=start, created_at__lte=end).count()

            page = request.GET.get('page', 1)
            paginator = Paginator(quest, 20)
            try:
                quest = paginator.page(page)
            except PageNotAnInteger:
                quest = paginator.page(1)
            except EmptyPage:
                quest = paginator.page(paginator.num_pages)
            context = {
                'u': u,
                'quest': quest,
                'count': count,
            }

            return render(request, 'survey/questionnaires.html', context)
        elif user.access_level.id == 2:
            fac = Partner_Facility.objects.filter(
                partner__in=Partner_User.objects.filter(user=user).values_list('name', flat=True))
            q = Facility_Questionnaire.objects.filter(facility_id__in=fac.values_list('facility_id', flat=True)
                                                      ).values_list('questionnaire_id').distinct()
            quest = Questionnaire.objects.filter(id__in=q, created_at__gte=start, created_at__lte=end).order_by('-created_at')
            count = quest.count()

            page = request.GET.get('page', 1)
            paginator = Paginator(quest, 20)
            try:
                quest = paginator.page(page)
            except PageNotAnInteger:
                quest = paginator.page(1)
            except EmptyPage:
                quest = paginator.page(paginator.num_pages)

            context = {
                'u': u,
                'quest': quest,
                'fac': fac,
                'count': count,
            }
            return render(request, 'survey/questionnaires.html', context)
    elif request.method == "GET":
        if user.access_level.id == 3:
            quest = Questionnaire.objects.all().order_by('-created_at')
            count = Questionnaire.objects.all().count()
            fac = Facility.objects.all()

            page = request.GET.get('page', 1)
            paginator = Paginator(quest, 20)
            try:
                quest = paginator.page(page)
            except PageNotAnInteger:
                quest = paginator.page(1)
            except EmptyPage:
                quest = paginator.page(paginator.num_pages)
            context = {
                'u': u,
                'quest': quest,
                'fac': fac,
                'count': count,
            }
            return render(request, 'survey/questionnaires.html', context)
        elif user.access_level.id == 2:
            fac = Partner_Facility.objects.filter(
                partner__in=Partner_User.objects.filter(user=user).values_list('name', flat=True))
            q = Facility_Questionnaire.objects.filter(facility_id__in=fac.values_list('facility_id', flat=True)
                                                      ).values_list('questionnaire_id').distinct()
            quest = Questionnaire.objects.filter(id__in=q).order_by('-created_at')
            count = quest.count()

            page = request.GET.get('page', 1)
            paginator = Paginator(quest, 20)
            try:
                quest = paginator.page(page)
            except PageNotAnInteger:
                quest = paginator.page(1)
            except EmptyPage:
                quest = paginator.page(paginator.num_pages)

            context = {
                'u': u,
                'quest': quest,
                'fac': fac,
                'count': count,
            }
            return render(request, 'survey/questionnaires.html', context)


@login_required
def add_question(request, q_id):
    user = request.user
    u = user
    if request.method == 'POST':
        question = request.POST.get('question')
        q_type = request.POST.get('q_type')  # For q_type 1 is opened ended 2 Radio 3 is Checkbox
        answers = request.POST.get('answers')
        if q_type == '1':
            answers = "Open Text"
        answers_list = answers.split(',')
        print(question, q_type, answers_list)

        q_save = Question.objects.create(question=question, question_type=q_type, created_by=user,
                                         questionnaire_id=q_id)
        trans_one = transaction.savepoint()
        question_id = q_save.pk

        if question_id:
            try:
                for f in answers_list:
                    fac_save = Answer.objects.create(question_id=question_id, created_by=user, option=f)
                    fac_save.save()
            except IntegrityError:
                transaction.savepoint_rollback(trans_one)
                return HttpResponse("error")
    if user.access_level.id == 2 and user.access_level.id != Questionnaire.objects.get(
            id=q_id).created_by.access_level.id:
        raise PermissionDenied
    try:
        Questionnaire.objects.get(id=q_id)
    except Questionnaire.DoesNotExist:
        raise Http404('Questionnaire does not exist')
    context = {
        'u': u,
        'questionnaire': q_id
    }
    return render(request, 'survey/new_questions.html', context)


@login_required
def edit_question(request, q_id):
    user = request.user
    try:
        q = Question.objects.get(id=q_id)
        quest_id = Questionnaire.objects.get(id=q.questionnaire_id).id
        ans = Answer.objects.filter(question=q).values_list('option', flat=True)
        a = ','.join([str(elem) for elem in ans])
        print(a)
    except Question.DoesNotExist:
        raise Http404('Question does not exist')
    except Questionnaire.DoesNotExist:
        raise Http404('Questionnaire does not exist')
    if user.access_level.id == 2:
        if Questionnaire.objects.get(id=q.questionnaire_id).created_by.access_level.id == 3:
            raise PermissionDenied
    if request.method == 'POST':
        question = request.POST.get('question')
        q_type = request.POST.get('q_type')  # For q_type 1 is opened ended 2 Radio 3 is Checkbox
        answers = request.POST.get('answers')
        if q_type == '1':
            answers = "Open Text"
        answers_list = answers.split(',')

        print(question, q_type, answers_list)
        trans_one = transaction.savepoint()

        q.question = question
        q.question_type = q_type

        q.save()

        try:
            Answer.objects.filter(question=q).delete()
            for f in answers_list:
                fac_save = Answer.objects.create(question=q, created_by=user, option=f)
                fac_save.save()
        except IntegrityError:
            transaction.savepoint_rollback(trans_one)
            return HttpResponse("error")

    context = {
        'u': user,
        'q': q,
        'questionnaire': quest_id,
        'ans': a,
    }
    return render(request, 'survey/edit_questions.html', context)


@login_required
def question_list(request, q_id):
    user = request.user
    u = user
    if user.access_level.id == 3:
        quest = Question.objects.filter(questionnaire_id=q_id).order_by('-created_at')
        context = {
            'u': u,
            'quest': quest,
            'questionnaire': q_id,
        }
        print(quest)
        return render(request, 'survey/question_list.html', context)
    elif user.access_level.id == 2:
        try:
            quest = Question.objects.filter(questionnaire=Questionnaire.objects.get(id=q_id)).order_by('-created_at')
        except Questionnaire.DoesNotExist:
            raise Http404("Questionnaire Does not exist")
        if Questionnaire.objects.get(id=q_id).created_by.access_level.id == 3:
            raise PermissionDenied

        context = {
            'u': u,
            'quest': quest,
            'questionnaire': q_id,
        }
        return render(request, 'survey/question_list.html', context)
