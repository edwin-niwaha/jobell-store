# Djoser social-auth compatibility wheel

`djoser-2.3.4-py3-none-any.whl` contains unmodified upstream Djoser 2.3.4
application code and its MIT license. Only `METADATA` and `RECORD` differ.

The upstream release requires `social-auth-app-django>=5.0.0,<6.0.0`, which
forces social-auth-core 4.x. The production audit identified five advisories in
that dependency; upstream fixes require social-auth-core 5.x. This wheel changes
only the dependency declaration to `social-auth-app-django>=6.1.0,<7.0.0`.
Jobell does not expose Djoser's optional social-provider API. Its existing user
and JWT endpoints remain enabled; browser Google login uses social_django.

This is a project-maintained compatibility patch, not an upstream-supported
dependency combination. API registration/JWT and CSRF-protected social login
regression tests cover the paths Jobell uses. Remove this wheel and return to a
normal PyPI dependency when Djoser publishes a compatible release.

Rebuild with `python scripts/build_djoser_compat.py`. The script verifies the
official upstream SHA256, makes the one metadata replacement, regenerates RECORD,
and writes a deterministic archive. The Docker build verifies `djoser.sha256`.
Audit the installed environment with `python -m pip_audit --local`; the unchanged
Djoser code is audited as version 2.3.4, alongside the installed patched social
libraries. Do not hide audit findings or use a resolver override at deployment.

Upstream SHA256: `251e4a8973f95d1d770413fd219599413a4affb6dcf04d1ea6479258a133a919`

Patched SHA256: `b22bf6329ef404d096d89f8b13bb90709f0c2d15c51e42d62d791c94f5034ac5`

Sources: [Djoser package](https://pypi.org/project/djoser/2.3.4/),
[upstream dependency declaration](https://github.com/sunscrapers/djoser/blob/2.3.4/pyproject.toml),
[social-auth security fixes](https://github.com/python-social-auth/social-core/blob/master/CHANGELOG.md),
[social_django 6.0 changes](https://github.com/python-social-auth/social-app-django/releases/tag/6.0.0).
