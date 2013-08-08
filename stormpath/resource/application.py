from .base import Resource, ResourceList, StatusMixin
from .password_reset_token import PasswordResetTokenList
from .login_attempt import LoginAttemptList
from ..error import Error


class Application(Resource, StatusMixin):
    """Application resource.

    More info in documentation:
    https://www.stormpath.com/docs/python/product-guide#Applications
    """

    writable_attrs = ('name', 'description', 'status')

    def get_resource_attributes(self):
        from .tenant import Tenant
        from .account import AccountList
        from .group import GroupList
        from .account_store_mapping import AccountStoreMappingList, \
            AccountStoreMapping

        return {
            'tenant': Tenant,
            'accounts': AccountList,
            'groups': GroupList,
            'password_reset_tokens': PasswordResetTokenList,
            'login_attempts': LoginAttemptList,
            'account_store_mappings': AccountStoreMappingList,
            'default_account_store_mapping': AccountStoreMapping,
            'default_group_store_mapping': AccountStoreMapping,
        }

    def authenticate_account(self, login, password):
        """Authenticate Account inside the Application.

        :param login: Username or email address

        :param password: Unencrypted user password

        """
        try:
            return self.login_attempts.basic_auth(login, password).account
        except Error as e:
            if e.status_code == 400:
                return None
            else:
                raise

    def send_password_reset_email(self, email):
        """Send a password reset email.

        More info in documentation:
        http://www.stormpath.com/docs/rest/product-guide#PasswordReset

        :param email: Email address to send the email to

        """
        token = self.password_reset_tokens.create({'email': email})
        return token.account

    def verify_password_reset_token(self, token):
        """Verify password reset by using a token.

        :param token: password reset token extracted from the url

        """

        try:
            return self.password_reset_tokens[token].account
        except Error as e:
            if e.status_code == 404:
                return None
            else:
                raise


class ApplicationList(ResourceList):
    """Application resource list.
    """
    create_path = '/applications'
    resource_class = Application
