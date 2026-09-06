from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Create a new user account with a hashed password and the default role."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    role = serializers.CharField(source='role.code', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'password', 'password2', 'role',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Ensure password and password2 match before hitting create()."""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': "Passwords don't match."})
        data.pop('password2')
        return data

    def create(self, validated_data):
        """Create the user via create_user so the password is hashed."""
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)
