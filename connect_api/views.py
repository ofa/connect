from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from connect_api.serializers import GroupSerializer, UserSerializer
from open_connect.groups.models import *


class UserList(generics.ListAPIView):
    myUser = get_user_model()
    queryset = myUser.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveDestroyAPIView):
    myUser = get_user_model()
    queryset = myUser.objects.all()
    serializer_class = UserSerializer


class GroupList(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class GroupDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


@api_view(['GET'])
def group_owners(request, group_id):
    if request.method == 'GET':
        owners = Group.objects.get(id=group_id).owners
        owners_data = UserSerializer(owners, many=True)

    return Response({"Owners": owners_data.data})


@api_view(['GET'])
def groups_a_user_is_member(request, user_id):
    if request.method == 'GET':
        groups = get_user_model().objects.get(id=user_id).groups_joined
        groups_list_data = GroupSerializer(groups, many=True)

        return Response({'Groups by user': groups_list_data.data})


@api_view(['GET'])
def group_members(request, group_id):
    if request.method == 'GET':
        members_list = Group.objects.get(id=group_id).get_members()
        members_list_data = UserSerializer(members_list, many=True)

        return Response({'Members list': members_list_data.data})


@api_view(['GET', 'POST', 'DELETE'])
def add_user_to_group(request, group_id, user_id):
    if request.method == 'POST':
        user = get_user_model().objects.get(id=user_id)
        user.add_to_group(group_id)
        
        return Response({"Member added": user_id})

    if request.method == 'DELETE':
        user = get_user_model().objects.get(id=user_id)
        user.remove_from_group(group_id)
        return Response({"Removed": user_id})

    return Response({"User": user_id, "Group": group_id})
