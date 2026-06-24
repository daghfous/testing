# pylint: disable=no-member
"""
Test saml server
"""
import copy
from typing import List
import pytest

from ateme.um_backend.types import IdpType
from ateme.um_backend.types import RolesMapper
from ateme.um_backend.request_utils import HttpHeaders
from tests.conftest import init_log_record, get_activity_log

IDP_NAME = 'azd'
# user auth0: pfs@ateme.com AdminA0!
CERT = """
       MIIDHTCCAgWgAwIBAgIJQVu6HOKprI+RMA0GCSqGSIb3DQEBCwUAMCwxKjAoBgNV
       BAMTIWRldi1vcXQ0MHJsa3R6MnAzM3A1LnVzLmF1dGgwLmNvbTAeFw0yMzExMDIx
       NDM2MzNaFw0zNzA3MTExNDM2MzNaMCwxKjAoBgNVBAMTIWRldi1vcXQ0MHJsa3R6
       MnAzM3A1LnVzLmF1dGgwLmNvbTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoC
       ggEBAKJz4FCF7JsMtM8iP6fVtU8iYO0wGBXWeIQdqZVZX1NL0h0WmoKEVPBnVpoe
       NTRDeDEv9FD7zvMDwpziEXYcr9pwyJdvOaFZc4ptLx0j8yk+3I4FjNohQvcWpzt2
       zdt23uiB6KpyUViZdtdAaWbaeCpY4Mz4TDC/12iXMGM8G4QkTUR3Y1XCiFOzc9bx
       DkbkWBcxZMhUaeH4ljLD7YI7gSZmVcR4Rv1V2HOmIZMZ3KcBW8f5M/+8WbghzPOZ
       wwZhfT9ke3Ny5WaElub6jd52STQP12LbZR/Sne7ttG1dIo0/hlGPolyUQl3biniw
       CTbzma+dEM1DCbTXxlrWZylgqhcCAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAd
       BgNVHQ4EFgQUugrkqWSmeQHExC51sz5IoFZn2HUwDgYDVR0PAQH/BAQDAgKEMA0G
       CSqGSIb3DQEBCwUAA4IBAQB1szLlGtBYip8rk92ofynG5Ocg1yNr/NyT70mAwBxH
       sKpJzjczviUFYUNxaWI5D7t9SmU6+fUHrCfiv4zNvazDZIuu9JENRGNHxdi1uLng
       F0aqjs1PgKvZjyvmndYGSkp74fvbEeKzPV5vERIXAAgq/MF7kpHF6IDWDxKuIdSn
       9XbGjuoyI86FLboAHnAtKvrgsDd3e3XXkEuPQpYPuUb1g0HC9ZHoV7m17TqjCpD7
       zuzO7A8YTx2M4jyMtOx/r9ocg03jhap9wB2wadavxQuA/fu5H/QGPYZbG6Sfx6cr
       E9YZbXXhGwxWuvJWKQz3a1gkkT7fDIVDwXYsarRGa+QP</X509Certificate>
"""

DIRECT_MAPPER = {
    'type': 'direct',
    'attribute_name': 'roles'
}

SIMPLE_MAPPER = {
    'type': 'simple',
    'attributes': [{'name': r'path.to.nested_property\.with\.dot', 'value': 'value'}],
    'scopes_to_add': ['usr:guest'],
}

# pylint: disable=line-too-long
PUBLIC_KEY = "-----BEGIN CERTIFICATE-----MIICQjCCAaugAwIBAgIBADANBgkqhkiG9w0BAQ0FADA+MQswCQYDVQQGEwJmcjEPMA0GA1UECAwGZnJhbmNlMQ4wDAYDVQQKDAVhdGVtZTEOMAwGA1UEAwwFYXRlbWUwHhcNMjMxMTIwMTAyNjAyWhcNMjQxMTE5MTAyNjAyWjA+MQswCQYDVQQGEwJmcjEPMA0GA1UECAwGZnJhbmNlMQ4wDAYDVQQKDAVhdGVtZTEOMAwGA1UEAwwFYXRlbWUwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAK8+5/hA8jTs0CDA/ZWRcjss1yvW583/I6p/Q3cNf3R4PcqJQ0vnd2zX0I5EiBKpYalHHERxaIamtFVPWjyf9bM7IZQFA8mDbHYsmruYvUmk0QEVD+jd6Yzbdr4B6F2Vp7tjxX/wm/LKseV9iqWdMsBGWBJ0UCLfGT26R5oQ5yX/AgMBAAGjUDBOMB0GA1UdDgQWBBS0J761Ngiup4GtsMNFbfO2IU/CqTAfBgNVHSMEGDAWgBS0J761Ngiup4GtsMNFbfO2IU/CqTAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBDQUAA4GBAJNocFVP434R7DLfQUj6xXUYTTClf0xcmDukG4KEriKe/IrbevdVQqpffhFc1v53eAPMgY5GDkZNDQXh/2b/cQBXPxYNXafTRXsmcMpkvWc9VGKkQA0Wak730Rxy1V/jUf6m2Jlb1VxdRZbatGcB4Ik9ubzKH1SLTLQSUD2smR2h-----END CERTIFICATE-----"
PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAK8+5/hA8jTs0CDA/ZWRcjss1yvW583/I6p/Q3cNf3R4PcqJQ0vnd2zX0I5EiBKpYalHHERxaIamtFVPWjyf9bM7IZQFA8mDbHYsmruYvUmk0QEVD+jd6Yzbdr4B6F2Vp7tjxX/wm/LKseV9iqWdMsBGWBJ0UCLfGT26R5oQ5yX/AgMBAAECgYBdt96GPPVKqHqFibATlLzqOIi5wSwmVhPU0kpaGLXYq5UgA1gh958+bgvyiWPb1wmLZaQQVjX4DJ7UIKO5WDIkzGzutQlv72x84kkPE4sfiX4x3AkXx1hShF7sXEIKZ9m/5hyfGnyUwBOLgL4jZRkmz/WyFLJDPm6GFzcCaorngQJBAOV1A7xiepSFVqxBDVi5MUxWPhi7qIZfz4e9soM68UPi5k/eGkfGEMHg/DMG6nA+7QEiaNxYNznJdgsgeWHU+kkCQQDDhINp77/DZUA7w361oLwLXO+N+978ygDmrJfUlln1D90VkMJ1nsj9mDQ7E3LtZryW/AgQbYyCh8kLcQjywd4HAkA+175vMNV7qc0kHijmnMnYq2IUagjszH7NIXIrqM/9FL6ZLy4pbCCYyOKpowJAPauxfNgVSP/PDtMKlxlHZwopAkBjrPPeFxb5Q24qybCYYfhcBqYuCWEWGNm6v/SrsXbtA4hfjSxGEIxBFM5T68dklkLA6n4l+eNvTFBHX/oC4KkTAkEAmIbwHSz7iULRlC4bLAgPS/NnhngN+D1QE1i7NbScAof0oQaLq5trggqQKBbjT+UUii+0F9Tc1zBmJIlRjt2p3A==-----END PRIVATE KEY-----"
SAML_RESPONSE = "PHNhbWxwOlJlc3BvbnNlIHhtbG5zOnNhbWxwPSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6cHJvdG9jb2wiIElEPSJfMmZlNDI4Njg2NzQxNjE3MWExZWQiICBJblJlc3BvbnNlVG89Ik9ORUxPR0lOXzEyNGRiYTljMTQxMmQwNjRlOGRhNTVhOWFiM2E4YjA1ODdlYWFiY2IiICBWZXJzaW9uPSIyLjAiIElzc3VlSW5zdGFudD0iMjAyMy0xMS0xNFQwODo0MjowMi4zMDhaIiAgRGVzdGluYXRpb249Imh0dHA6Ly8xNzIuMjkuNzEuMTEwL3BtZi1lbHovdXNlcnMvYXNzZXJ0aW9uX2NvbnN1bWVyX3NlcnZpY2UiPjxzYW1sOklzc3VlciB4bWxuczpzYW1sPSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6YXNzZXJ0aW9uIj51cm46ZGV2LW9xdDQwcmxrdHoycDMzcDUudXMuYXV0aDAuY29tPC9zYW1sOklzc3Vlcj48c2FtbHA6U3RhdHVzPjxzYW1scDpTdGF0dXNDb2RlIFZhbHVlPSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6c3RhdHVzOlN1Y2Nlc3MiLz48L3NhbWxwOlN0YXR1cz48c2FtbDpBc3NlcnRpb24geG1sbnM6c2FtbD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmFzc2VydGlvbiIgVmVyc2lvbj0iMi4wIiBJRD0iX3Q3UTh1b21RNHpUYUUxT05DNHA2a2ZOVUhaUGtoTG9KIiBJc3N1ZUluc3RhbnQ9IjIwMjMtMTEtMTRUMDg6NDI6MDIuMjk4WiI+PHNhbWw6SXNzdWVyPnVybjpkZXYtb3F0NDBybGt0ejJwMzNwNS51cy5hdXRoMC5jb208L3NhbWw6SXNzdWVyPjxTaWduYXR1cmUgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvMDkveG1sZHNpZyMiPjxTaWduZWRJbmZvPjxDYW5vbmljYWxpemF0aW9uTWV0aG9kIEFsZ29yaXRobT0iaHR0cDovL3d3dy53My5vcmcvMjAwMS8xMC94bWwtZXhjLWMxNG4jIi8+PFNpZ25hdHVyZU1ldGhvZCBBbGdvcml0aG09Imh0dHA6Ly93d3cudzMub3JnLzIwMDEvMDQveG1sZHNpZy1tb3JlI3JzYS1zaGEyNTYiLz48UmVmZXJlbmNlIFVSST0iI190N1E4dW9tUTR6VGFFMU9OQzRwNmtmTlVIWlBraExvSiI+PFRyYW5zZm9ybXM+PFRyYW5zZm9ybSBBbGdvcml0aG09Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvMDkveG1sZHNpZyNlbnZlbG9wZWQtc2lnbmF0dXJlIi8+PFRyYW5zZm9ybSBBbGdvcml0aG09Imh0dHA6Ly93d3cudzMub3JnLzIwMDEvMTAveG1sLWV4Yy1jMTRuIyIvPjwvVHJhbnNmb3Jtcz48RGlnZXN0TWV0aG9kIEFsZ29yaXRobT0iaHR0cDovL3d3dy53My5vcmcvMjAwMS8wNC94bWxlbmMjc2hhMjU2Ii8+PERpZ2VzdFZhbHVlPnordEZDcGxNTW1hR3VtQmlVbHFFYnUyZndLbWNTLzRTY0lYb0o1WHY1S2c9PC9EaWdlc3RWYWx1ZT48L1JlZmVyZW5jZT48L1NpZ25lZEluZm8+PFNpZ25hdHVyZVZhbHVlPmdxU1dmWG53NU9UV3dnOUt5WnJaUEFHWXVIaS9NQ0RrZCtzTUdkMFIxUEhPVlEyMW5KZGU0cnRsYzZKb1VtMmRSOFNYbEpPekFjZnhFc2ZrdlhKUFRBZ25laFIxOTc0NG92LzcwNTFCUHZzeFppekhSSTZkKzBPT3dSY0FUYkY0UUs4UUJ0aVJKNjNtU1M5N3pRbE1MdmxvVXRyTWJPV3VvTWxIbm01WEFDZnExV1NGNmpBU3Zhc0d1RTUwUy9aS3owZFJoVWM5RWc3K2hPdVhRcGYvM0x1NnJlcTdDSFlOc2t4cDQraGtucTdPclpwbTJQSElQNndvQjhOMnB2RTQ1Mm1VNDZieTFnSU5PYWthRXJ1MmJlM1hRbndBN29jZ1NwUTh0Y3czd3hjK1BtMi9WaGhXemZld1NxdjFpTUUzUVBpZ3Y1TVl5NzRtZ3N3M1B3V2tqUT09PC9TaWduYXR1cmVWYWx1ZT48S2V5SW5mbz48WDUwOURhdGE+PFg1MDlDZXJ0aWZpY2F0ZT5NSUlESFRDQ0FnV2dBd0lCQWdJSlFWdTZIT0twckkrUk1BMEdDU3FHU0liM0RRRUJDd1VBTUN3eEtqQW9CZ05WQkFNVElXUmxkaTF2Y1hRME1ISnNhM1I2TW5Bek0zQTFMblZ6TG1GMWRHZ3dMbU52YlRBZUZ3MHlNekV4TURJeE5ETTJNek5hRncwek56QTNNVEV4TkRNMk16TmFNQ3d4S2pBb0JnTlZCQU1USVdSbGRpMXZjWFEwTUhKc2EzUjZNbkF6TTNBMUxuVnpMbUYxZEdnd0xtTnZiVENDQVNJd0RRWUpLb1pJaHZjTkFRRUJCUUFEZ2dFUEFEQ0NBUW9DZ2dFQkFLSno0RkNGN0pzTXRNOGlQNmZWdFU4aVlPMHdHQlhXZUlRZHFaVlpYMU5MMGgwV21vS0VWUEJuVnBvZU5UUkRlREV2OUZEN3p2TUR3cHppRVhZY3I5cHd5SmR2T2FGWmM0cHRMeDBqOHlrKzNJNEZqTm9oUXZjV3B6dDJ6ZHQyM3VpQjZLcHlVVmlaZHRkQWFXYmFlQ3BZNE16NFREQy8xMmlYTUdNOEc0UWtUVVIzWTFYQ2lGT3pjOWJ4RGtia1dCY3haTWhVYWVINGxqTEQ3WUk3Z1NabVZjUjRSdjFWMkhPbUlaTVozS2NCVzhmNU0vKzhXYmdoelBPWnd3WmhmVDlrZTNOeTVXYUVsdWI2amQ1MlNUUVAxMkxiWlIvU25lN3R0RzFkSW8wL2hsR1BvbHlVUWwzYmluaXdDVGJ6bWErZEVNMURDYlRYeGxyV1p5bGdxaGNDQXdFQUFhTkNNRUF3RHdZRFZSMFRBUUgvQkFVd0F3RUIvekFkQmdOVkhRNEVGZ1FVdWdya3FXU21lUUhFeEM1MXN6NUlvRlpuMkhVd0RnWURWUjBQQVFIL0JBUURBZ0tFTUEwR0NTcUdTSWIzRFFFQkN3VUFBNElCQVFCMXN6TGxHdEJZaXA4cms5Mm9meW5HNU9jZzF5TnIvTnlUNzBtQXdCeEhzS3BKempjenZpVUZZVU54YVdJNUQ3dDlTbVU2K2ZVSHJDZml2NHpOdmF6RFpJdXU5SkVOUkdOSHhkaTF1TG5nRjBhcWpzMVBnS3Zaanl2bW5kWUdTa3A3NGZ2YkVlS3pQVjV2RVJJWEFBZ3EvTUY3a3BIRjZJRFdEeEt1SWRTbjlYYkdqdW95STg2Rkxib0FIbkF0S3ZyZ3NEZDNlM1hYa0V1UFFwWVB1VWIxZzBIQzlaSG9WN20xN1RxakNwRDd6dXpPN0E4WVR4Mk00anlNdE94L3I5b2NnMDNqaGFwOXdCMndhZGF2eFF1QS9mdTVIL1FHUFlaYkc2U2Z4NmNyRTlZWmJYWGhHd3hXdXZKV0tRejNhMWdra1Q3ZkRJVkR3WFlzYXJSR2ErUVA8L1g1MDlDZXJ0aWZpY2F0ZT48L1g1MDlEYXRhPjwvS2V5SW5mbz48L1NpZ25hdHVyZT48c2FtbDpTdWJqZWN0PjxzYW1sOk5hbWVJRCBGb3JtYXQ9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjEuMTpuYW1laWQtZm9ybWF0OnVuc3BlY2lmaWVkIj5hdXRoMHw2NTQzYjRiMzNjMWI4NDA5YmFlMmZmNTA8L3NhbWw6TmFtZUlEPjxzYW1sOlN1YmplY3RDb25maXJtYXRpb24gTWV0aG9kPSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6Y206YmVhcmVyIj48c2FtbDpTdWJqZWN0Q29uZmlybWF0aW9uRGF0YSBOb3RPbk9yQWZ0ZXI9IjIwMjMtMTEtMTRUMDk6NDI6MDIuMjk4WiIgUmVjaXBpZW50PSJodHRwOi8vMTcyLjI5LjcxLjExMC9wbWYtZWx6L3VzZXJzL2Fzc2VydGlvbl9jb25zdW1lcl9zZXJ2aWNlIiBJblJlc3BvbnNlVG89Ik9ORUxPR0lOXzEyNGRiYTljMTQxMmQwNjRlOGRhNTVhOWFiM2E4YjA1ODdlYWFiY2IiLz48L3NhbWw6U3ViamVjdENvbmZpcm1hdGlvbj48L3NhbWw6U3ViamVjdD48c2FtbDpDb25kaXRpb25zIE5vdEJlZm9yZT0iMjAyMy0xMS0xNFQwODo0MjowMi4yOThaIiBOb3RPbk9yQWZ0ZXI9IjIwMjMtMTEtMTRUMDk6NDI6MDIuMjk4WiI+PHNhbWw6QXVkaWVuY2VSZXN0cmljdGlvbj48c2FtbDpBdWRpZW5jZT51cm46YXV0aDA6ZGV2LW9xdDQwcmxrdHoycDMzcDU6cGZzPC9zYW1sOkF1ZGllbmNlPjwvc2FtbDpBdWRpZW5jZVJlc3RyaWN0aW9uPjwvc2FtbDpDb25kaXRpb25zPjxzYW1sOkF1dGhuU3RhdGVtZW50IEF1dGhuSW5zdGFudD0iMjAyMy0xMS0xNFQwODo0MjowMi4yOThaIiBTZXNzaW9uSW5kZXg9Il9NcVlhVDRuVzJrbkVzc1NIT3dlWHNqbjFORnVBYzkxbCI+PHNhbWw6QXV0aG5Db250ZXh0PjxzYW1sOkF1dGhuQ29udGV4dENsYXNzUmVmPnVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphYzpjbGFzc2VzOnVuc3BlY2lmaWVkPC9zYW1sOkF1dGhuQ29udGV4dENsYXNzUmVmPjwvc2FtbDpBdXRobkNvbnRleHQ+PC9zYW1sOkF1dGhuU3RhdGVtZW50PjxzYW1sOkF0dHJpYnV0ZVN0YXRlbWVudCB4bWxuczp4cz0iaHR0cDovL3d3dy53My5vcmcvMjAwMS9YTUxTY2hlbWEiIHhtbG5zOnhzaT0iaHR0cDovL3d3dy53My5vcmcvMjAwMS9YTUxTY2hlbWEtaW5zdGFuY2UiPjxzYW1sOkF0dHJpYnV0ZSBOYW1lPSJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciIgTmFtZUZvcm1hdD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmF0dHJuYW1lLWZvcm1hdDp1cmkiPjxzYW1sOkF0dHJpYnV0ZVZhbHVlIHhzaTp0eXBlPSJ4czpzdHJpbmciPmF1dGgwfDY1NDNiNGIzM2MxYjg0MDliYWUyZmY1MDwvc2FtbDpBdHRyaWJ1dGVWYWx1ZT48L3NhbWw6QXR0cmlidXRlPjxzYW1sOkF0dHJpYnV0ZSBOYW1lPSJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9lbWFpbGFkZHJlc3MiIE5hbWVGb3JtYXQ9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphdHRybmFtZS1mb3JtYXQ6dXJpIj48c2FtbDpBdHRyaWJ1dGVWYWx1ZSB4c2k6dHlwZT0ieHM6c3RyaW5nIj5wZnNAYXRlbWUuY29tPC9zYW1sOkF0dHJpYnV0ZVZhbHVlPjwvc2FtbDpBdHRyaWJ1dGU+PHNhbWw6QXR0cmlidXRlIE5hbWU9Imh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWUiIE5hbWVGb3JtYXQ9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphdHRybmFtZS1mb3JtYXQ6dXJpIj48c2FtbDpBdHRyaWJ1dGVWYWx1ZSB4c2k6dHlwZT0ieHM6c3RyaW5nIj5wZnNAYXRlbWUuY29tPC9zYW1sOkF0dHJpYnV0ZVZhbHVlPjwvc2FtbDpBdHRyaWJ1dGU+PHNhbWw6QXR0cmlidXRlIE5hbWU9Imh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL3VwbiIgTmFtZUZvcm1hdD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmF0dHJuYW1lLWZvcm1hdDp1cmkiPjxzYW1sOkF0dHJpYnV0ZVZhbHVlIHhzaTp0eXBlPSJ4czpzdHJpbmciPnBmc0BhdGVtZS5jb208L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48c2FtbDpBdHRyaWJ1dGUgTmFtZT0iaHR0cDovL3NjaGVtYXMuYXV0aDAuY29tL2lkZW50aXRpZXMvZGVmYXVsdC9jb25uZWN0aW9uIiBOYW1lRm9ybWF0PSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6YXR0cm5hbWUtZm9ybWF0OnVyaSI+PHNhbWw6QXR0cmlidXRlVmFsdWUgeHNpOnR5cGU9InhzOnN0cmluZyI+VXNlcm5hbWUtUGFzc3dvcmQtQXV0aGVudGljYXRpb248L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48c2FtbDpBdHRyaWJ1dGUgTmFtZT0iaHR0cDovL3NjaGVtYXMuYXV0aDAuY29tL2lkZW50aXRpZXMvZGVmYXVsdC9wcm92aWRlciIgTmFtZUZvcm1hdD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmF0dHJuYW1lLWZvcm1hdDp1cmkiPjxzYW1sOkF0dHJpYnV0ZVZhbHVlIHhzaTp0eXBlPSJ4czpzdHJpbmciPmF1dGgwPC9zYW1sOkF0dHJpYnV0ZVZhbHVlPjwvc2FtbDpBdHRyaWJ1dGU+PHNhbWw6QXR0cmlidXRlIE5hbWU9Imh0dHA6Ly9zY2hlbWFzLmF1dGgwLmNvbS9pZGVudGl0aWVzL2RlZmF1bHQvaXNTb2NpYWwiIE5hbWVGb3JtYXQ9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphdHRybmFtZS1mb3JtYXQ6dXJpIj48c2FtbDpBdHRyaWJ1dGVWYWx1ZSB4c2k6dHlwZT0ieHM6Ym9vbGVhbiI+ZmFsc2U8L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48c2FtbDpBdHRyaWJ1dGUgTmFtZT0iaHR0cDovL3NjaGVtYXMuYXV0aDAuY29tL2NsaWVudElEIiBOYW1lRm9ybWF0PSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6YXR0cm5hbWUtZm9ybWF0OnVyaSI+PHNhbWw6QXR0cmlidXRlVmFsdWUgeHNpOnR5cGU9InhzOnN0cmluZyI+Q2hKcDNEVGFsUHZ1VzRieUtvWHc4MHZaSHlWSXZCaTY8L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48c2FtbDpBdHRyaWJ1dGUgTmFtZT0iaHR0cDovL3NjaGVtYXMuYXV0aDAuY29tL2NyZWF0ZWRfYXQiIE5hbWVGb3JtYXQ9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphdHRybmFtZS1mb3JtYXQ6dXJpIj48c2FtbDpBdHRyaWJ1dGVWYWx1ZSB4c2k6dHlwZT0ieHM6YW55VHlwZSI+VGh1IE5vdiAwMiAyMDIzIDE0OjM5OjQ3IEdNVCswMDAwIChDb29yZGluYXRlZCBVbml2ZXJzYWwgVGltZSk8L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48c2FtbDpBdHRyaWJ1dGUgTmFtZT0iaHR0cDovL3NjaGVtYXMuYXV0aDAuY29tL2VtYWlsX3ZlcmlmaWVkIiBOYW1lRm9ybWF0PSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6YXR0cm5hbWUtZm9ybWF0OnVyaSI+PHNhbWw6QXR0cmlidXRlVmFsdWUgeHNpOnR5cGU9InhzOmJvb2xlYW4iPmZhbHNlPC9zYW1sOkF0dHJpYnV0ZVZhbHVlPjwvc2FtbDpBdHRyaWJ1dGU+PHNhbWw6QXR0cmlidXRlIE5hbWU9Imh0dHA6Ly9zY2hlbWFzLmF1dGgwLmNvbS9uaWNrbmFtZSIgTmFtZUZvcm1hdD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmF0dHJuYW1lLWZvcm1hdDp1cmkiPjxzYW1sOkF0dHJpYnV0ZVZhbHVlIHhzaTp0eXBlPSJ4czpzdHJpbmciPnBmczwvc2FtbDpBdHRyaWJ1dGVWYWx1ZT48L3NhbWw6QXR0cmlidXRlPjxzYW1sOkF0dHJpYnV0ZSBOYW1lPSJodHRwOi8vc2NoZW1hcy5hdXRoMC5jb20vcGljdHVyZSIgTmFtZUZvcm1hdD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmF0dHJuYW1lLWZvcm1hdDp1cmkiPjxzYW1sOkF0dHJpYnV0ZVZhbHVlIHhzaTp0eXBlPSJ4czpzdHJpbmciPmh0dHBzOi8vcy5ncmF2YXRhci5jb20vYXZhdGFyLzRlNDQzYjM4MTI4ZTkyMWQxMGVkMTlkYWVjNjZkYjcwP3M9NDgwJmFtcDtyPXBnJmFtcDtkPWh0dHBzJTNBJTJGJTJGY2RuLmF1dGgwLmNvbSUyRmF2YXRhcnMlMkZwZi5wbmc8L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48c2FtbDpBdHRyaWJ1dGUgTmFtZT0iaHR0cDovL3NjaGVtYXMuYXV0aDAuY29tL3VwZGF0ZWRfYXQiIE5hbWVGb3JtYXQ9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphdHRybmFtZS1mb3JtYXQ6dXJpIj48c2FtbDpBdHRyaWJ1dGVWYWx1ZSB4c2k6dHlwZT0ieHM6YW55VHlwZSI+TW9uIE5vdiAxMyAyMDIzIDEwOjIzOjUwIEdNVCswMDAwIChDb29yZGluYXRlZCBVbml2ZXJzYWwgVGltZSk8L3NhbWw6QXR0cmlidXRlVmFsdWU+PC9zYW1sOkF0dHJpYnV0ZT48L3NhbWw6QXR0cmlidXRlU3RhdGVtZW50Pjwvc2FtbDpBc3NlcnRpb24+PC9zYW1scDpSZXNwb25zZT4="
LOGOUT_RESPONSE = "fZJRS+wwEIX/Ssl7mjTbNk1oe5GryMKqcFd8uC+STBNdbpuUnRT9+bd28UEQH2fImXO+mbRopnHWh/gSl/TH4RwDumx/3ZFnBXZwlVHUD4WhpeUlNdYJyhuvZAUenAWSPbkznmLoiMg5yfaIi9sHTCaktcVFSXlBefXIGy245nWu6uovya4dplMwaVO+pjSjZqyQIhcql0VeFJzNk6fwwhZcDdhHSgZmHK2Bf1v1a4qD68Yt9+obPrM/xo483N8cHm7398/CgzKlakrHd34nYefW7FB5I50YhKht3QAokCR7n8aAeltGR5Zz0NHgCXUwk0OdQB+v7g56RdTzOaYIcSR9u8GeL9KfRQZXig9Y0n/CYsL87RSG+IZ5cIkp5T1YbmldeEtLIzlVg/VUcu52jSwNOMVadvHs28vZjsmkBb9Wv9e9ZE9mXNzPmXB7rY8LgEMkrG/Z16Hsu6/R/wc="


@pytest.fixture(name="saml_config")
def _saml_config():
    """ saml_config fixture """
    return {
        'idp_name': IDP_NAME,
        'entity_id': "urn:dev-oqt40rlktz2p33p5.us.auth0.com",
        'single_sign_on_service':
            "https://dev-oqt40rlktz2p33p5.us.auth0.com/samlp/ChJp3DTalPvuW4byKoXw80vZHyVIvBi6",
        'single_logout_service':
            "https://dev-oqt40rlktz2p33p5.us.auth0.com/samlp/ChJp3DTalPvuW4byKoXw80vZHyVIvBi6/logout",
        'cert_fingerprint': CERT,
        'idp_type': IdpType.saml.name,
        'idp_label': "SAML server"
    }


@pytest.mark.parametrize("with_sp_cert", [True, False])
@pytest.mark.parametrize(
    "single_sign_on_service, expected_status",
    [pytest.param(
        "https://testmss.onelogin.com/trust/saml2/http-post/sso/1294683c-a895-43cd-bfb1-180b7fce5444",
        200),
     pytest.param("bad_sso", 406)])
async def test_validate_saml(init_backend_with_admin, saml_config, single_sign_on_service: str, expected_status, with_sp_cert):
    """
    Test the idp saml config validation
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    if with_sp_cert:
        saml_config['sign_authn_request'] = True
        saml_config['sign_logout_request'] = True
        saml_config['sp_public_cert'] = PUBLIC_KEY
        saml_config['sp_private_cert'] = PRIVATE_KEY
    saml_config['single_sign_on_service'] = single_sign_on_service
    resp = await _api.post(
        "/idpconfigs/validate", json=saml_config, headers=_admin_headers
    )
    assert resp.status == expected_status


@pytest.mark.parametrize("status_code", [200, 400])
async def test_saml_metadata(init_backend_with_admin, saml_config, status_code):
    """
    Test Saml metadata generation
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    saml_body = saml_config
    if status_code > 200:
        saml_body = copy.deepcopy(saml_config)
        saml_body['single_sign_on_service'] = 'bad_url'
    # create saml config
    resp = await _api.post("/idpconfigs", json=saml_body, headers=_admin_headers)
    assert resp.status == 201

    # get and check saml metadata
    resp = await _api.get(
        f"/idp_metadata/{IDP_NAME}",
        headers=_admin_headers,
    )
    assert resp.status == status_code
    saml_metadata = await resp.text()

    if status_code == 200:
        assert saml_metadata.startswith(
            '<?xml version="1.0"?>\n<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"\n')


async def test_crud_saml_configs(init_backend_with_admin, saml_config):
    # pylint: disable=too-many-statements
    """
    Test Post/Get/Patch/Delete saml configs
    """
    _api, _api_backend, _admin_token = init_backend_with_admin
    _user = "admin"
    _idp_name = "local"
    _headers = {
        "Authorization": f"Bearer {_admin_token}",
        HttpHeaders.X_USER: _user,
        HttpHeaders.X_IDP_NAME: _idp_name
    }

    async def get_saml_config_by_name(saml_config_name):
        resp = await _api.get(
            f"/idpconfigs/{saml_config_name}",
            headers=_headers,
        )
        assert resp.status == 200
        return await resp.json()

    async def patch_saml_config_by_name(saml_config_name, body):

        body["idp_type"] = IdpType.saml.name
        resp = await _api.patch(
            f"/idpconfigs/{saml_config_name}",
            json=body,
            headers=_headers,
        )
        assert resp.status == 200
        return await resp.text()

    # create saml config
    q, handler = init_log_record()
    resp = await _api.post("/idpconfigs", json=saml_config, headers=_headers)
    assert resp.status == 201

    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} added idp configuration {saml_config['idp_name']}"

    # check get saml config
    resp = await _api.get("/idpconfigs", headers=_headers)
    assert resp.status == 200
    result = await resp.json()
    idp_types = [config['idp_type'] for config in result]
    assert IdpType.saml.name in idp_types

    # check get saml config with its idp_name
    result = await get_saml_config_by_name(IDP_NAME)
    assert result['idp_name'] == IDP_NAME

    # Test create user associated to saml config, not allowed for saml
    resp = await _api.post(
        "/users",
        json=[{"username": "johndoe", "idp_name": IDP_NAME}],
        headers=_headers,
    )
    assert resp.status == 400

    # check get idp sso url
    relay_state = "http://172.29.71.110/pmf-elz"
    resp = await _api.get(
        f"/idp_sso/{IDP_NAME}?relay_state={relay_state}",
        headers=_headers,
    )
    assert resp.status == 403

    # patch saml config - update label and deny access to True
    q, handler = init_log_record()
    patch_config = {'deny_access': True, 'idp_label': 'new label'}
    await patch_saml_config_by_name(IDP_NAME, patch_config)
    result = await get_saml_config_by_name(IDP_NAME)
    assert result['idp_label'] == patch_config['idp_label']
    assert result['deny_access'] == patch_config['deny_access']
    log = get_activity_log(q, handler)
    assert log.message == (f"{_user}:{_idp_name} updated idp configuration {saml_config['idp_name']}, "
                           f"set default behavior to deny access")

    # patch saml config - update deny access to False and set scopes
    q, handler = init_log_record()
    patch_config = {'deny_access': False, "scopes": ["usr:engineer", "usr:monitor"]}
    await patch_saml_config_by_name(IDP_NAME, patch_config)
    result = await get_saml_config_by_name(IDP_NAME)
    assert result['deny_access'] == patch_config['deny_access']

    log = get_activity_log(q, handler)
    assert log.message == (f"{_user}:{_idp_name} updated idp configuration {saml_config['idp_name']}, "
                           f"set default behavior to add default roles with roles usr:engineer, usr:monitor, to allow access")

    # patch saml config - add direct mapper
    q, handler = init_log_record()
    patch_config = {'mappers': [DIRECT_MAPPER]}
    await patch_saml_config_by_name(IDP_NAME, patch_config)
    result = await get_saml_config_by_name(IDP_NAME)
    patch_config['mappers'] = copy.deepcopy(result['mappers'])  # Add IDs for next update
    existing_mapper_ids = [mapper.pop('_id') for mapper in result['mappers']]
    assert result['mappers'] == [DIRECT_MAPPER]
    assert len(existing_mapper_ids) == len(result['mappers'])  # Ensure an ID has been generated
    log = get_activity_log(q, handler)
    assert log.message == (f"{_user}:{_idp_name} updated idp configuration {saml_config['idp_name']}, "
                           f"set default behavior with mappers direct/unknown_id")

    # patch saml config - add simple mapper
    q, handler = init_log_record()
    patch_config['mappers'].append(SIMPLE_MAPPER)
    await patch_saml_config_by_name(IDP_NAME, patch_config)
    result = await get_saml_config_by_name(IDP_NAME)
    patch_config['mappers'] = copy.deepcopy(result['mappers'])  # Add IDs for next update
    new_mapper_ids = [mapper.pop('_id') for mapper in result['mappers']]
    assert result['mappers'] == [DIRECT_MAPPER, SIMPLE_MAPPER]
    assert len(new_mapper_ids) == len(result['mappers'])  # Ensure an ID has been generated
    for id_ in existing_mapper_ids:  # Ensure existing IDs have not changed
        assert id_ in new_mapper_ids
    existing_mapper_ids = new_mapper_ids
    log = get_activity_log(q, handler)
    assert log.message == (f"{_user}:{_idp_name} updated idp configuration azd, "
                           f"set default behavior with mappers direct/unknown_id, simple/unknown_id")

    # update saml config - update mappers
    patch_config['mappers'][0]['attribute_name'] = 'scopes'
    patch_config['mappers'][1]['attributes'][0]['value'] = 'value2'
    patch_config['mappers'][1]['scopes_to_add'] = ['usr:guest', 'all:operator']
    await patch_saml_config_by_name(IDP_NAME, patch_config)
    result = await get_saml_config_by_name(IDP_NAME)

    assert result['mappers'][0]['attribute_name'] == patch_config['mappers'][0]['attribute_name']
    assert (result['mappers'][1]['attributes'][0]['value']
            == patch_config['mappers'][1]['attributes'][0]['value'])
    assert (sorted(result['mappers'][1]['scopes_to_add'])
            == sorted(patch_config['mappers'][1]['scopes_to_add']))
    patch_config['mappers'] = copy.deepcopy(result['mappers'])  # Add IDs for next update
    new_mapper_ids = [mapper.pop('_id') for mapper in result['mappers']]
    assert len(new_mapper_ids) == len(result['mappers'])  # Ensure an ID has been generated
    for id_ in existing_mapper_ids:  # Ensure existing IDs have not changed
        assert id_ in new_mapper_ids
    existing_mapper_ids = new_mapper_ids

    # update saml config - delete mapper
    del patch_config['mappers'][-1]
    await patch_saml_config_by_name(IDP_NAME, patch_config)
    result = await get_saml_config_by_name(IDP_NAME)
    new_mapper_ids = [mapper.pop('_id') for mapper in result['mappers']]
    assert len(new_mapper_ids) == 1
    assert new_mapper_ids[0] in existing_mapper_ids  # Ensure ID has not changed

    # try to patch with invalid data: 'domain' is a ldap property
    resp = await _api.patch(
        f"/idpconfigs/{IDP_NAME}",
        json={"idp_type": "saml", "domain": "ateme.com"},
        headers=_headers,
    )
    assert resp.status == 400

    # try to patch with invalid data: missing idp_type
    resp = await _api.patch(
        f"/idpconfigs/{IDP_NAME}",
        json={"domain": "invalid"},
        headers=_headers,
    )
    assert resp.status == 400

    # try to patch with ldap idp_type for this saml config
    q, handler = init_log_record()
    resp = await _api.patch(
        f"/idpconfigs/{IDP_NAME}",
        json={"idp_type": "ldap"},
        headers=_headers,
    )
    assert resp.status == 400
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} failed to update idp configuration {saml_config['idp_name']}"

    # delete saml config
    q, handler = init_log_record()
    resp = await _api.delete(
        f"/idpconfigs/{IDP_NAME}",
        headers=_headers
    )
    assert resp.status == 200
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} removed idp configuration {saml_config['idp_name']}"

    # failed to delete saml config
    q, handler = init_log_record()
    resp = await _api.delete(
        f"/idpconfigs/{IDP_NAME}",
        headers=_headers
    )
    assert resp.status == 404
    log = get_activity_log(q, handler)
    assert log.message == f"{_user}:{_idp_name} failed to remove idp configuration {saml_config['idp_name']}"


@pytest.mark.parametrize("with_sp_cert", [True, False])
@pytest.mark.parametrize("status_code", [200, 404])
@pytest.mark.parametrize("mode, method", [('login', 'post'), ('logout', 'post'), ('logout', 'get')])
async def test_saml_login_logout(init_backend_with_admin, init_database, saml_config, status_code: int, with_sp_cert: bool, mode: str, method: str):
    """
    Test login/logout with saml configs
    """
    # pylint: disable=too-many-locals,too-many-arguments
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}
    _db = init_database
    if with_sp_cert:
        saml_config['sign_authn_request'] = True
        saml_config['sign_logout_request'] = True
        saml_config['sp_public_cert'] = PUBLIC_KEY
        saml_config['sp_private_cert'] = PRIVATE_KEY
    relay_state = str(_api.server.make_url("/ping"))
    login_body = {"SAMLResponse": SAML_RESPONSE,
                  "RelayState": relay_state}
    username = "pfs@ateme.com"

    saml_config['automatically_add_user'] = True
    saml_config['entity_id'] += str(_api.server.make_url("/ping"))
    saml_config['deny_access'] = False

    # create saml config
    resp = await _api.post("/idpconfigs", json=saml_config, headers=_admin_headers)
    assert resp.status == 201

    # check get idp sso url
    resp = await _api.get(
        f"/idp_sso/{IDP_NAME}?relay_state={relay_state}",
        headers=_admin_headers,
    )
    assert resp.status == 403

    # Login
    if status_code == 404:
        login_body["SAMLResponse"] = "fake"

    _login_body = login_body if method == 'post' else None
    headers = {"Content-type":  "application/x-www-form-urlencoded"} if method == 'post' \
        else _admin_headers
    query_params = f"?SAMLResponse={LOGOUT_RESPONSE}&RelayState={relay_state}" if method == 'get' else ''
    resp = await _api.request(
        method,
        f"/saml/callback/{IDP_NAME}{query_params}",
        data=_login_body,
        headers=headers
    )

    assert resp.history[0].status == 302
    assert str(resp.url) == relay_state

    if mode == 'login':
        if status_code == 200:
            for _auth_key in ['access_token', 'refresh_token', 'expires_in', 'token_type', 'username']:
                assert _auth_key in str(resp.history[0].headers.getall('Set-Cookie'))
        else:
            assert 'saml_error' in resp.history[0].headers['Set-Cookie']

    # Assert that the user has been created
    if mode == 'login' and status_code == 200:
        resp = await _api.get(
            f"/users/{IDP_NAME}/{username}",
            headers=_admin_headers,
        )
        assert resp.status == status_code
        user = await resp.json()
        assert user['username'] == username
        db_user = await _db.get_user_by_name(username, IDP_NAME)
        saml_tokens = await _db.collection_tokens.get_list_by_user_id(db_user['user_id'])
        saml_headers = {"content-type": "application/json",
                        "Authorization": f"Bearer {saml_tokens[0].token}"}

        # Logout
        relay_state = "http://172.29.71.110/pmf-elz"
        resp = await _api.delete(
            f"/logout?relay_state={relay_state}", headers=saml_headers
        )
        assert resp.status == 200
        response = await resp.json()
        assert 'slo_url' in response

    # delete saml config
    resp = await _api.delete(
        f"/idpconfigs/{IDP_NAME}", headers=_admin_headers
    )
    assert resp.status == 200
    # Assert that the user has been deleted
    resp = await _api.get(
        f"/users/{IDP_NAME}/{username}",
        headers=_admin_headers,
    )
    assert resp.status == 404


@pytest.mark.parametrize("role_mappers, deny_access, saml_payload, cookie_expected, scopes_expected", [
    # Check when the default behavior is set to "Access Forbidden" if we don't match roles mapper
    # we don't create user and set error on cookie during redirect
    pytest.param(
        [
            {
                "type": "direct",
                "attribute_name": "roles"
            }
        ],
        True,
        {},
        "Access Forbidden",
        [],
        id="direct-access-forbidden"
    ),
    # Check that user have the default scope when no roles mapper match and deny access is False.
    pytest.param(
        [
            {
                "type": "direct",
                "attribute_name": "roles"
            }
        ],
        False,
        {},
        "access_token",
        ["all:guest"],
        id="direct-default-scopes"
    ),
    # Check a direct mapper match with attribute
    pytest.param(
        [
            {
                "type": "direct",
                "attribute_name": "roles"
            }
        ],
        False,
        {
            "attributes": [
                {"name": "roles", "value": "all:engineer"},
            ]
        },
        "access_token",
        ["all:engineer"],
        id="direct-match"
    ),
    # Check a direct mapper with inexsting scopes
    pytest.param(
        [
            {
                "type": "direct",
                "attribute_name": "roles"
            }
        ],
        False,
        {
            "attributes": [
                {"name": "roles", "value": "all:nonexist"},
            ]
        },
        "access_token",
        ["all:guest"],
        id="direct-scope-nonexist"
    ),
    # A simple mapper with scopes to add which match with attributes
    pytest.param(
        [
            {
                "type": "simple",
                "attributes": [{"name": "username", "value": "admin"}],
                "scopes_to_add": ["all:administrator"]
            }
        ],
        False,
        {
            "attributes": [
                {"name": "username", "value": "admin"},
            ]
        },
        "access_token",
        ["all:administrator"],
        id="simple-match"
    ),
    # Mix a direct and simple mapper, check that scopes are append
    pytest.param(
        [
            {
                "type": "simple",
                "attributes": [{"name": "username", "value": "admin"}],
                "scopes_to_add": ["all:administrator"]
            },
            {
                "type": "direct",
                "attribute_name": "roles",
            },
        ],
        False,
        {
            "attributes": [
                {"name": "username", "value": "admin"},
                {"name": "roles", "value": "all:engineer"},
            ]
        },
        "access_token",
        ["all:administrator", "all:engineer"],
        id="multiple-match"
    ),
    # Mix a direct and simple mapper, check that scopes are append
    pytest.param(
        [
            {
                "type": "simple",
                "attributes": [{"name": "username", "value": "admin"}],
                "scopes_to_add": ["all:administrator"]
            },
            {
                "type": "direct",
                "attribute_name": "roles",
            },
        ],
        False,
        {
            "attributes": [
                {"name": "username", "value": "admin"},
                {"name": "roles", "value": ["all:engineer", "all:guest"]},
            ]
        },
        "access_token",
        ["all:administrator", "all:engineer", "all:guest"],
        id="multiple-match-with-direct-list"
    ),
    # Simple mapper with no match and access forbidden as default behavior
    pytest.param(
        [
            {
                "type": "simple",
                "attributes": [{"name": "username", "value": "admin"}],
                "scopes_to_add": ["all:administrator"]
            }
        ],
        True,
        {
            "attributes": [
                {"name": "username", "value": "johndoe"},
            ]
        },
        "Access Forbidden",
        [],
        id="simple-access-forbidden"
    )
],
    indirect=["saml_payload"])
async def test_saml_login_with_role_mappers(  # pylint: disable=too-many-arguments
    init_backend_with_admin,
    saml_config,
    role_mappers: List[RolesMapper],
    deny_access: bool,
    saml_payload: str,
    cookie_expected: str,
    scopes_expected: List[str],
):
    """
    Test login with different roles mapper on idp config. Check that scopes associated to user
    in case of successfully login and match roles mapping on user attributes.
    """
    _api, _, _admin_token = init_backend_with_admin
    _admin_headers = {"Authorization": f"Bearer {_admin_token}"}

    relay_state = str(_api.server.make_url("/ping"))
    username = "pfs@ateme.com"
    login_body = {"SAMLResponse": saml_payload,
                  "RelayState": relay_state}

    saml_config['automatically_add_user'] = True
    saml_config['entity_id'] += str(_api.server.make_url("/ping"))
    saml_config['deny_access'] = deny_access
    saml_config['mappers'] = role_mappers

    # create saml config
    resp = await _api.post("/idpconfigs", json=saml_config, headers=_admin_headers)
    assert resp.status == 201

    resp = await _api.request(
        path=f"/saml/callback/{IDP_NAME}",
        method="POST",
        data=login_body,
        headers={"Content-type":  "application/x-www-form-urlencoded"}
    )
    # Check that we have been redirected
    assert resp.history
    assert resp.history[0].status == 302
    assert resp.history[0].headers["Location"] == relay_state
    assert cookie_expected in resp.history[0].headers["Set-Cookie"]

    # Assert that the user has been created
    resp = await _api.get(
        f"/users/{IDP_NAME}/{username}",
        headers=_admin_headers,
    )
    assert resp.status == (200 if not deny_access else 404)

    if not deny_access:
        user = await resp.json()
        assert user['username'] == username
        assert sorted(user['scopes']) == sorted(scopes_expected)
