import hashlib

from rest_framework.throttling import SimpleRateThrottle


class PasswordResetIPThrottle(SimpleRateThrottle):
    scope = "password_reset_ip"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class PasswordResetEmailThrottle(SimpleRateThrottle):
    scope = "password_reset_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email")

        if not isinstance(email, str):
            return None

        normalized_email = email.strip().casefold()

        if not normalized_email:
            return None

        email_hash = hashlib.sha256(
            normalized_email.encode("utf-8")
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": email_hash,
        }