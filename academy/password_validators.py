from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
)


class StrongAdminPasswordValidator:
    VALIDATORS = [
        UserAttributeSimilarityValidator,
        MinimumLengthValidator,
        CommonPasswordValidator,
        NumericPasswordValidator,
    ]

    def validate(self, password, user=None):
        if user and user.is_staff:
            for validator in self.VALIDATORS:
                validator().validate(password, user)

    def get_help_text(self):
        return "Admins must have a strong password."
