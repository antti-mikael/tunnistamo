import collections

from allauth.account.models import EmailAddress
from allauth.socialaccount.providers.base import Provider, ProviderAccount
from django.urls import reverse
from django.conf import settings as django_settings

from suomifi_provider.suomifi_uri import MAP


def get_single_value(data, keys, default=None):
    """Returns the value from the first found key in the data. Or default if none of the keys are found.
    Returns the first item if the found value is a collection."""
    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        if key in data:
            value = data[key]
            # Just take the first item if the value is a collection
            if isinstance(value, collections.Sequence) and not isinstance(value, str):
                value = next(iter(value))

            return value

    return default


class SuomiFiAccount(ProviderAccount):
    def get_profile_url(self):
        return None

    def get_avatar_url(self):
        return None

    def to_str(self):
        return get_single_value(self.account.extra_data, 'displayName', '')


class SuomiFiProvider(Provider):
    id = 'suomifi'
    name = 'Suomi.fi-tunnistus'
    account_class = SuomiFiAccount

    def get_login_url(self, request, next=None, **kwargs):
        return reverse('suomifi_login')

    def extract_uid(self, data):
        """
        Extracts the unique user ID from `data`
        """
        if MAP['to']['electronicIdentificationNumber'] in data:
            return get_single_value(data, MAP['to']['electronicIdentificationNumber'])

        if MAP['to']['nationalIdentificationNumber'] in data:
            return get_single_value(data, MAP['to']['nationalIdentificationNumber'])

        if MAP['to']['uid'] in data:
            return get_single_value(data, MAP['to']['uid'])

        raise ValueError('No uid found in SAML attributes')

    def extract_extra_data(self, data):
        """
        Extracts fields from `data` that will be stored in
        `SocialAccount`'s `extra_data` JSONField.

        :return: any JSON-serializable Python structure.
        """
        friendly_data = {}
        for key, value in data.items():
            if key in MAP['fro'].keys():
                key = MAP['fro'][key]

            friendly_data[key] = value

        return friendly_data

    def extract_common_fields(self, data):
        """
        Extracts fields from `data` that will be used to populate the
        `User` model in the `SOCIALACCOUNT_ADAPTER`'s `populate_user()`
        method.

        For example:

            {'first_name': 'John'}

        :return: dictionary of key-value pairs.
        """
        common_fields = {
            'first_name': get_single_value(data, [MAP['to']['givenName'], MAP['to']['FirstName']]),
            'last_name': get_single_value(data, MAP['to']['sn']),
            'email': get_single_value(data, [MAP['to']['mail'], MAP['to']['email']]),
            'name': get_single_value(data, MAP['to']['displayName']),
        }

        return common_fields

    def extract_email_addresses(self, data):
        email = get_single_value(data, [MAP['to']['email'], MAP['to']['email']])

        if email:
            return [EmailAddress(email=email, verified=False, primary=True)]

        return []

    def get_saml_settings_dict(self, request):
        # Can't import until now because this file is imported by the provider registry before models are available
        from suomifi_provider.models import SamlSettings

        app = self.get_app(request)

        try:
            app_saml_settings = SamlSettings.objects.get(app=app)
        except SamlSettings.DoesNotExist:
            raise RuntimeError("Saml settings for app {} do not exist. Please create it in the admin.".format(app))

        languages = [i[0] for i in django_settings.LANGUAGES]

        app_saml_settings.set_current_language(languages[0])

        acs_url = request.build_absolute_uri(reverse("suomifi_acs"))
        sls_url = request.build_absolute_uri(reverse("suomifi_sls"))

        settings_dict = {
            "sp": {
                "entityId": app_saml_settings.sp_entity_id,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": sls_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "attributeConsumingService": {
                    "serviceName": app_saml_settings.service_name,
                    "requestedAttributes": [
                        {
                            "name": MAP['to']['displayName'],
                            "friendlyName": "displayName",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['electronicIdentificationNumber'],
                            "friendlyName": "electronicIdentificationNumber",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['nationalIdentificationNumber'],
                            "friendlyName": "nationalIdentificationNumber",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['cn'],
                            "friendlyName": "cn",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['givenName'],
                            "friendlyName": "givenName",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['FirstName'],
                            "friendlyName": "FirstName",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['mail'],
                            "friendlyName": "mail",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                        {
                            "name": MAP['to']['email'],
                            "friendlyName": "email",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                        },
                    ],
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:transient",
                "x509cert": app_saml_settings.sp_certificate,
                "privateKey": app_saml_settings.sp_private_key,
            },
            "idp": {
                "entityId": app_saml_settings.idp_entity_id,
                "singleSignOnService": {
                    "url": app_saml_settings.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": app_saml_settings.idp_sls_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": app_saml_settings.idp_certificate,
            },
            # TODO: make configurable
            "strict": True,
            "debug": True,
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": True,
                "logoutRequestSigned": True,
                "logoutResponseSigned": True,
                "signMetadata": True,
                "wantMessagesSigned": True,
                "wantAssertionsSigned": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "wantAssertionsEncrypted": True,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2000/09/xmldsig#sha1",
                "requestedAuthnContext": False,
            },
            "contactPerson": {
                "technical": {
                    "givenName": app_saml_settings.technical_contact_name,
                    "emailAddress": app_saml_settings.technical_contact_email,
                },
                "support": {
                    "givenName": app_saml_settings.support_contact_name,
                    "emailAddress": app_saml_settings.support_contact_email,
                }
            },
            "organization": {
                # Set below
            },
            # Custom SuomiFi settings
            "service_name": {
            },
            "ui": {
                "logo": app_saml_settings.ui_logo_url,
            },
        }

        for lang in languages:
            app_saml_settings.set_current_language(lang)

            settings_dict['organization'][lang] = {
                "name": app_saml_settings.organization_name,
                "displayname": app_saml_settings.organization_display_name,
                "url": app_saml_settings.organization_url,
            }

            settings_dict['service_name'][lang] = app_saml_settings.service_name

            settings_dict['ui'][lang] = {
                "displayname": app_saml_settings.ui_display_name,
                "description": app_saml_settings.ui_description,
                "privacy_statement_url": app_saml_settings.ui_privacy_statement_url,
            }

        return settings_dict


provider_classes = [SuomiFiProvider]
