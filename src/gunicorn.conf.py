bind = '0.0.0.0:65442'
forwarded_allow_ips = '*'
secure_scheme_headers = {'X-FORWARDED-PROTOCOL': 'ssl', 'X-FORWARDED-PROTO': 'https', 'X-FORWARDED-SSL': 'on'}
workers = 4
keep_alive = 5
