<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Script pre_upgrade_job](#script-pre_upgrade_job)
    - [Overview](#overview)
    - [Parameters](#parameters)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Script [pre_upgrade_job](backend/ateme/um_backend/scripts/pre_upgrade_job/__main__.py)

This script is used specifically for upgrade of the UM from version 4.x or [5.x, 8.x] and then to 9.x

### Overview

From the version 5.0 of the User-Management:
1. `idp_config` replaces `ldap_config` with two additional fields: `idp_type`, `idp_name`. 
2. For `user` collection: 
    * `idp_name` is created from `domain`
    * `authenticate_mode` is replaced by `idp_type`
    * `domain` is removed 
    * `user_id` is regenerated 

From the version 9.0 of the User-Management
1. The ```password_policy``` dict is added having the default values 
```json
{"expiration_delay_in_days": -1, "regex_pattern": "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[#$^+=!*()@%&])\S{,255}$"}
``` 
2. The ```password_expiration``` field is removed 

### Parameters

This script takes several parameters:

```bash
optional arguments:
  -h, --help                 show this help message and exit
  --database-url DB_URL            Database url, default value: 'mongodb://localhost:27017'  
  --database-name DB_NAME          Database name, default_value: 'users'
```

For database-url and database-name, you can set the environment variables UM_DATABASE_URL and UM_DATABASE_NAME instead of passing the arguments. 
