export default {
  common: {
    user: 'user',
    users: 'users',
    action: 'action',
    actions: 'actions',
    role: 'role',
    roles: 'roles',
    idp: 'idp',
    idps: 'idps',
    cancel: 'Cancel',
    save: 'Save',
    saving: 'Saving...',
    saved: 'Saved',
    cantSave: "Couldn't be saved",
    delete: 'Delete',
    deleteTitleM: 'Click to delete a {{name}}',
    deleteTitleF: 'Click to delete a {{name}}',
    deleteSelectedTitleM: 'Click to delete selected {{name}}',
    deleteSelectedTitleF: 'Click to delete selected {{name}}',
    duplicate: 'Duplicate',
    duplicating: 'Duplicating...',
    duplicated: 'Duplicated',
    cantDuplicate: "Can't duplicate",
    duplicateTitleM: 'Duplicate a {{name}}',
    duplicateTitleF: 'Duplicate a {{name}}',
    add: 'Add',
    addTitleM: 'Click to add a {{name}}',
    addTitleF: 'Click to add a {{name}}',
    addSelectedTitleM: 'Click to add selected {{name}}',
    addSelectedTitleF: 'Click to add selected {{name}}',
    editWithName: 'Edit {{name}}',
    duplicateWithName: 'Duplicate {{name}}'
  },
  users: {
    versionTooltip: 'Version: {{version}}',
    table: {
      actions: {
        edit: 'Click to edit {{name}}',
        delete: 'Click to delete {{name}}',
        duplicate: 'Click to duplicate {{name}}'
      }
    },
    confirmationMessageBeginning: 'Are you sure you want to delete',
    confirmCard: {
      cancelLabel: 'No',
      confirmLabel: 'Yes'
    },
    deleteAction: {
      confirmationMessageRole: 'the selected action?'
    },
    deleteRole: {
      confirmationMessageRole: 'the selected role?'
    },
    deleteUser: {
      confirmationMessageUsers: 'selected users?'
    },
    errors: {
      required: 'This field is required',
      invalidFormat: 'Invalid format',
      deleteAdmin: 'You cannot delete an administrator.',
      deleteRole: 'Failed to delete user role.',
      fieldMandatory: 'Field is mandatory',
      passwordMustBeDifferent: 'The new password must be different from the old one',
      passwordsMatch: 'Passwords do not match.',
      wrongFormat: 'Not valid password format.',
      badRequest: '400 Bad Request.',
      notFound: '404 Not Found.',
      serverError: 'Server Error.',
      alreadyExistMapper: 'This mapper already exists.'
    },
    inputs: {
      mode: {
        title: 'Mode'
      },
      idp_name: {
        title: 'IdP name',
        description: 'Identity provider name of the user'
      },
      password: {
        description:
          "Password from {{min_length}} to 255 characters long, using:\n - at least one lower case letter,\n - one upper case letter,\n - one digit,\n - at least one special character {'(#$^+=!*()@%&)'}, \n - no space",
        title: 'Password'
      },
      passwordConfirmation: {
        title: 'Password confirmation',
        description: 'Password confirmation'
      },

      newPassword: {
        description:
          "Password from 8 to 255 characters long, using:\n - at least one lower case letter,\n - one upper case letter,\n - one digit,\n - at least one special character {'(#$^+=!*()@%&)'}, \n - no space",
        title: 'New password'
      },
      newPasswordConfirmation: {
        title: 'New password confirmation',
        description: 'Password confirmation'
      },
      role: {
        title: "The user's role"
      },
      username: {
        description:
          'Username from 3 to 255 characters long, using:\n- lower/uppercase letters and numbers\n- no special character besides -._\n- no space',
        title: 'Username'
      }
    },
    idp: {
      columns: {
        type: 'Type',
        name: 'Name',
        label: 'Label'
      },
      errors: {
        existingIdp: 'IdP {{idp_name}} already exists.'
      },
      pending: 'Saving IdP configuration.',
      rejected: 'IdP configuration could not be saved: {{reason}}.',
      resolved: 'IdP configuration saved.',
      template: {
        ldapInformations: 'LDAP informations',
        samlInformations: 'SAML informations',
        ldap_address: {
          description: 'This parameter contains the LDAP protocol, the name or IP address of the server and its port.',
          title: 'Name or IP address (+ Port)'
        },
        entity_id: {
          description: 'Identifier of the Identity provider entity (usually an url)',
          title: 'IdP Id'
        },
        single_sign_on_service: {
          title: 'IdP url used to sign on',
          description: 'URL Target of the Identity provider where the Authentication Request Message will be sent'
        },
        single_logout_service: {
          title: 'IdP url used to logout',
          description: 'URL Location where the Logout Request from the Identity Provider will be sent'
        },
        cert_fingerprint: {
          title: 'IdP certificate',
          description: 'Public certificate of the Identity Provider'
        },
        sign_authn_request: {
          title: 'Sign auth request',
          description: 'Determines whether the authentication request must be signed'
        },
        sign_logout_request: {
          title: 'Sign logout request',
          description: 'Determines whether the logout request must be signed'
        },
        sp_public_cert: {
          title: 'Public certificate of the SP',
          description: 'Public certificate of the Service Provider'
        },
        sp_private_cert: {
          title: 'Private certificate of the SP',
          description: 'Private certificate of the Service Provider'
        },
        idp_type: {
          title: 'IdP type',
          description: 'The type of the Identity Provider'
        },
        idp_name: {
          title: 'Name',
          description:
            'This field is used to specify the unique name of the Identity Provider. It can only contain alphanumeric characters and the following characters: _.-'
        },
        idp_label: {
          title: 'Label',
          description: 'This field is used to specify a user friendly label of the Identity provider'
        },
        autoAddUsers: {
          description: 'This checkbox determines if the users must be created automatically with chosen roles',
          title: 'Add Users Automatically'
        },
        baseDn: {
          description: 'This field specifies the DN of the sub-node search starting.',
          title: 'Base DN'
        },
        bindDn: {
          description:
            'Optional DN (Distinguished Name) to use during the LDAP search. If empty, the credentials of the user trying to connect will be used.',
          title: 'Bind DN'
        },
        bindPassword: {
          description:
            'Optional password to use during the LDAP search. If empty, the credentials of the user trying to connect will be used.',
          title: 'Bind password'
        },
        userFilter: {
          description: 'Filter that will be used to search for the username during the LDAP request',
          title: 'User filter'
        },
        searchFilter: {
          description: 'Filter that will be used to filter LDAP users',
          title: 'Search filter'
        },
        columns: {
          address: 'Name or IP address',
          baseDN: 'Base DN',
          domain: 'Domain',
          group: 'Group',
          useSSL: 'Use SSL'
        },
        domain: {
          description: 'This parameter contains the LDAP domain.',
          title: 'Domain'
        },
        form: {
          password: 'Password',
          testLogin: 'Test LDAP login',
          username: 'LDAP username'
        },
        group: {
          description: 'This field determines the LDAP group.',
          title: 'Group'
        },
        headerLabel: {
          add: 'Add IdP'
        },
        roles: {
          description: 'Update users roles with the new edited roles',
          label: 'Update users roles with the new edited roles!',
          title: 'Roles'
        },
        testConfig: 'Test configuration',
        testServer: 'Test Server',
        validateConfig: 'Validate configuration',
        useSsl: {
          description: 'This checkbox determines the use of ssl.',
          title: 'Use SSL'
        },
        view: {
          addNewConfig: 'Add new IdP config',
          clickToTest: 'Test Server'
        }
      },
      spMetadata: {
        spMetadata: 'Service Provider metadata',
        refreshMetadata: 'Refresh',
        redirectUri: {
          description: 'Service Provider URI to configure the Identity Provider',
          title: 'Redirect URI'
        },
        downloadSpMetadata: 'Download SP metadata',
        copyToClipboard: 'Copy redirect URI to clipboard',
        error: 'Unable to retrieve SP metadata. Please check the above configuration is valid.'
      },
      user: {
        name: {
          autocomplete: 'username',
          title: 'LDAP username'
        },
        password: {
          autocomplete: 'password',
          new: 'new-password',
          title: 'LDAP password'
        }
      },
      roleMapping: {
        defaultRoles: 'Default roles',
        mappers: 'Mappers',
        default: {
          title: 'Default behavior',
          question:
            'What action to take if no mapper define or Identity provider attributes do not match any mapper at the time of login ?',
          denyAccess: 'Deny access',
          rolesToAdd: 'Role(s) to add',
          addDefaultRoles: 'Add default role(s)',
          oneRoleMandatory: 'At least one role is mandatory'
        },
        mapper: {
          add: 'Add mapper',
          title: 'Mapper',
          type: {
            title: 'Type',
            direct: 'Direct',
            simple: 'Simple'
          },
          attributeName: 'Attribute name',
          attributeNameFormat:
            'Attribute name should start with an alphabetical character.\n' +
            'It can only contain alphanumeric characters and the following characters: ._\\\n' +
            'To access a nested property, you can use a dot: path.to.nested_property\n' +
            'To access a property with a dot in its name, you can use backslashes: path.to.nested_property\\.with\\.dot',
          attributeValue: 'Attribute value',
          rolesToAdd: 'Role(s) to add',
          oneRoleMandatory: 'At least one role is mandatory',
          addNew: 'Add new mapper',
          edit: 'Edit mapper',
          confirmDelete: 'Are you sure you want to delete this mapper?',
          mappersWarning: "You have to set the 'User filter' field in the LDAP details to make the mappers work."
        }
      }
    },
    main: {
      general: 'General',
      roles: 'Roles',
      actions: 'Actions',
      logOut: 'Log out',
      noFoundRole: '"{{id}}" not defined',
      sessionDeactivation: 'Disable session timeout',
      confirmCurrentSession: 'Your session will remain logged in indefinitely. Proceed?',
      confirmUserSession: 'User session will remain logged in indefinitely. Proceed?',
      passwordHeader: 'Password',
      submit: 'Submit',
      view: {
        role: 'Role',
        username: 'Username',
        oldPassword: 'Old password',
        changePassword: 'Change password',
        pendingPasswordChange: 'Pending password change'
      },
      create: {
        addNewUser: 'Add user',
        userAlreadyExists: 'User already exists',
        updatePwdWarning: 'User will have to update password upon first connection;\n',
        cantCreateUser: "Can't create user, there are some errors in the form"
      },
      edit: {
        details: 'Details',
        rolesMapping: 'Roles mapping',
        forceChangePassword: 'Force user to change password at next login',
        passwordExpiration: 'Password Never Expires'
      }
    },
    roles: {
      addRoles: 'Add roles',
      addActions: {
        title: 'Add actions',
        columns: {
          action: 'Action',
          label: 'Label',
          description: 'Description'
        }
      },
      addOtherActions: 'Add other actions',
      actionsTabName: 'Available actions',
      descriptionTitle: 'Description',
      headerLabel: 'Add role',
      labelTitle: 'Label',
      name: 'Roles',
      nameError: "Name must match alphanumerical pattern or '*'.",
      nameTitle: 'Name',
      prefixError: 'Prefix must be between {{min}} and {{max}} alphabetical characters.',
      prefixTitle: 'Prefix',
      roleApplicableTabName: 'Applicable to roles',
      roleExists: 'Role with such prefix AND name already exists',
      rolesTabName: 'Available roles',
      textTitle: 'Title',
      view: {
        basicMode: 'Basic mode',
        description: 'Description',
        expertMode: 'Expert Mode',
        label: 'Label',
        modeTitle: 'In expert mode show all Roles',
        title: 'Role'
      }
    },
    sessions: {
      view: {
        username: 'Username',
        idp_name: 'Idp name',
        ip: 'IP',
        started_date: 'Started date',
        expiration_date: 'Expiration date',
        deleteSession: 'Are you sure you want to delete this session ?'
      }
    },
    configuration: {
      logoutSettings: {
        title: 'Configuration',
        invalidCurrentUserDeactivationPeriod: 'The deactivation period value must be between -1 and 3600',
        invalidPasswordMinimumLength: 'The password minimum length must be superior than 10',
        invalidCurrentMaxSuccessiveFailedLogin:
          'The max successive failed login attempts value must be between 1 and 10',
        idleTimeout: {
          title: 'Idle timeout',
          description: 'the maximum inactivity time of user connection'
        },
        sessionTimeout: {
          title: 'Session timeout',
          description: 'maximum session timeout'
        },
        errorMessage: 'Idle Timeout must be lower or equal than Maximum Session Timeout',
        preferences: {
          pending: 'Updating configuration...',
          resolved: 'Configuration updated',
          rejected: 'Cannot update configuration'
        },
        passwordPolicy: {
          pending: 'Updating password policy',
          resolved: 'Password policy updated',
          rejected: 'Cannot update password policy'
        },
        maxSuccessiveFailedLogin: {
          title: 'Max successive failed login attempts',
          description: 'Maximum number of consecutive failed login attempts'
        },
        userDeactivation: {
          title: 'Enable user deactivation',
          description: 'Enable user deactivation'
        },
        forceChangePassword: {
          title: 'Force all users to change their password',
          description: 'Force all users to change their password'
        },
        userDeactivationPeriod: {
          title: 'User deactivation period (in seconds)',
          description: 'Period (in seconds) during the user is disabled after max_successive_failed_login'
        },
        noAdminMessage: 'Only administrators have permission to update this configuration.',
        pwdPolicy: {
          title: 'Password Policy'
        },
        pwdExpiration: {
          title: 'Password Expiration',
          description: 'Password expiration in days, (-1) if never expired'
        },
        pwdLength: {
          title: 'Password minimum length',
          description: 'Minimum password length'
        }
      },
      backupRestore: {
        main: {
          create: 'Create application backup file',
          label: 'Backup / Restore users',
          restore: 'Restore application from backup file'
        },
        backup: {
          title: 'Backup users',
          titleCard: 'Download a users system backup',
          template: {
            saveLocally: {
              title: 'Save locally'
            },
            save: {
              title: 'Save backup'
            }
          },
          buttonLabels: {
            save: 'Save backup',
            saving: 'Saving backup',
            saved: 'Saved backup',
            cannotSave: 'Cannot save backup'
          }
        },
        restore: {
          title: 'Restore users',
          titleCard: 'Restore application from backup file',
          buttonLabels: {
            restore: 'Restore users',
            restoring: 'Restoring users...',
            restored: 'Users restored',
            cannotRestore: 'Cannot restore users'
          },
          locally: 'Load locally',
          errors: {
            fileToBig: 'File is too big, even compressed: data cannot be send to restore Alarm Server.'
          },
          returnWarning: '(warning: {{warn}})',
          warningMessage: `Warning!
          This action is going to restore application with archived configuration
          and possible impacts to operations.`,
          confirmationMessage: 'Are you sure you want to restore the Alarm Server?'
        }
      }
    }
  }
}
