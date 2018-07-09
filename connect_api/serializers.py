from rest_framework import serializers
from open_connect.groups.models import *
from open_connect.accounts.models import *
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username')

    def create(self, validated_data):
        username = validated_data.get('username')
        instance = User.objects.create(username=username)
        return instance


class AuthGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthGroup
        fields = ('name',)


class GroupSerializer(serializers.ModelSerializer):
    owners = UserSerializer(many=True)
    members = serializers.SerializerMethodField()

    group = AuthGroupSerializer()

    class Meta:
        model = Group
        fields = ('id', 'group', 'description', 'created_by', 'status', 'owners', 'category', 'members')

    def create(self, validated_data):
        group_name = validated_data.get('group').get('name')
        created_by = validated_data.get('created_by')
        description = validated_data.get('description')
        instance = Group.objects.create(name=group_name, created_by=created_by, description=description)
        return instance

    def get_members(self, obj):
        members = obj.get_members()
        members_serializer = UserSerializer(members, many=True)

        # return the serialized representation of 'Members' objs
        return members_serializer.data
