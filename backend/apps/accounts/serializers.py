"""認証系のシリアライザ。

レスポンスに載せるユーザー表現は **どのエンドポイントでも同じ形**にしてある
（register / login / google / me）。フロントの `AuthContext` が
「どこから来た user か」を気にせず 1 つの型で扱えるようにするため。
"""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .exceptions import Unauthorized

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """自分自身を返すときの形（docs/05-api.md）。

    `has_password` と `providers` を載せておくと、あとから設定画面に
    「Google だけのアカウントにパスワードを設定する」導線を足しやすい。
    """

    has_password = serializers.SerializerMethodField()
    providers = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "has_password", "providers", "date_joined"]

    def get_has_password(self, user) -> bool:
        return user.has_usable_password()

    def get_providers(self, user) -> list[str]:
        return sorted(account.provider for account in user.social_accounts.all())


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # trim_whitespace=False。前後の空白もパスワードの一部として扱う
    # （DRF の既定は trim するので、登録時とログイン時で食い違う恐れがある）。
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )

    def validate_email(self, value: str) -> str:
        email = User.objects.normalize_email(value)
        # email は unique だが、大文字小文字の違いは別レコードとして通ってしまう。
        # DB 制約より前にここで弾いて、IntegrityError ではなく 400 にする。
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("このメールアドレスは既に使用されています。")
        return email

    def validate(self, attrs):
        # ★ validate_password の第 2 引数（user）を渡すのを省かない。
        #   省くと UserAttributeSimilarityValidator が**黙って何もしない**ので、
        #   メールアドレスそのものをパスワードにできてしまう。
        #   他フィールドの値が必要なので、フィールド単位ではなくここで検証する。
        candidate = User(email=attrs["email"], display_name=attrs.get("display_name", ""))
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            # ModelBackend は USERNAME_FIELD の値を `username` 引数で受け取る。
            # USERNAME_FIELD を email にしていても、キーワード名は username のまま。
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            # ★ どちらが間違っているかは返さない（docs/05-api.md）。
            #   「そのメールは登録済み」という情報を漏らさないため。
            raise Unauthorized("メールアドレスまたはパスワードが正しくありません。")
        attrs["user"] = user
        return attrs


class GoogleLoginSerializer(serializers.Serializer):
    # ブラウザが Google Identity Services から受け取った ID トークンをそのまま渡す。
    id_token = serializers.CharField(write_only=True, trim_whitespace=False)
