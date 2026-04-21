import oss2

from app.config import get_settings

_settings = get_settings()


def make_bucket() -> oss2.Bucket:
    auth = oss2.AuthV4(
        _settings.oss_access_key_id,
        _settings.oss_access_key_secret,
    )
    endpoint = (
        _settings.oss_internal_endpoint or _settings.oss_endpoint
    )
    return oss2.Bucket(
        auth,
        endpoint,
        _settings.oss_bucket,
        region=_settings.oss_region,
    )
