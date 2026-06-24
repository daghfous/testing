export default {
  users: {
    common: {
      user: 'utilisateur',
      users: 'utilisateurs',
      action: 'action',
      actions: 'actions',
      role: 'rôle',
      roles: 'rôles',
      idp: 'idp',
      idps: 'idps',
      cancel: 'Annuler',
      save: 'Sauvegarder',
      saving: 'Sauvegarde en cours...',
      saved: 'Sauvegardé',
      cantSave: 'Impossible de sauvegarder',
      delete: 'Supprimer',
      deleteTitleM: 'Cliquez pour supprimer un {{name}}',
      deleteTitleF: 'Cliquez pour supprimer une {{name}}',
      deleteSelectedTitleM: 'Cliquez pour supprimer les {{name}} séléctionnés',
      deleteSelectedTitleF: 'Cliquez pour supprimer les {{name}} séléctionnées',
      duplicate: 'Dupliquer',
      duplicating: 'Duplication...',
      duplicated: 'Dupliqué',
      cantDuplicate: 'Impossible de dupliquer',
      duplicateTitleM: 'Dupliquer un {{name}}',
      duplicateTitleF: 'Dupliquer une {{name}}',
      add: 'Ajouter',
      addTitleM: 'Cliquez pour ajouter un {{name}}',
      addTitleF: 'Cliquez pour ajouter une {{name}}',
      addSelectedTitleM: 'Cliquez pour ajouter les {{name}} séléctionnés',
      addSelectedTitleF: 'Cliquez pour ajouter les {{name}} séléctionnées',
      editWithName: 'Modifier {{name}}',
      duplicateWithName: 'Dupliquer {{name}}'
    },
    versionTooltip: 'Version: {{version}}',
    table: {
      actions: {
        edit: 'Cliquer pour modifier {{name}}',
        delete: 'Cliquer pour supprimer {{name}}',
        duplicate: 'Cliquer pour dupliquer {{name}}'
      }
    },
    confirmationMessageBeginning: 'Êtes-vous sûr de vouloir supprimer',
    confirmCard: {
      cancelLabel: 'Non',
      confirmLabel: 'Oui'
    },
    deleteAction: {
      confirmationMessageRole: "l'action sélectionnée ?"
    },
    deleteRole: {
      confirmationMessageRole: 'le rôle sélectionné ?'
    },
    deleteUser: {
      confirmationMessageUsers: 'les utilisateurs sélectionnés ?'
    },
    errors: {
      required: 'Ce champ est obligatoire',
      invalidFormat: 'Format invalide',
      deleteAdmin: 'Vous ne pouvez pas supprimer un administrateur.',
      deleteRole: "Impossible de supprimer le rôle de l'utilisateur.",
      fieldMandatory: 'Le champ est obligatoire',
      passwordMustBeDifferent: "Le nouveau mot de passe doit être différent de l'ancien.",
      passwordsMatch: 'Les mots de passe ne correspondent pas.',
      wrongFormat: "Le format de mot de passe n'est pas valide.",
      badRequest: '400 Bad Request.',
      notFound: '404 Not Found.',
      serverError: 'Server Error.',
      alreadyExistMapper: 'Un mappage avec ce nom existe déjà.'
    },
    inputs: {
      mode: {
        title: 'Mode'
      },
      idp_name: {
        title: "Nom de l'IdP",
        description: "Nom du fournisseur d'identité (IdP) de l'utilisateur"
      },
      password: {
        description:
          "Mot de passe de {{min_length}} à 255 caractères, utilisant :\n - au moins une lettre minuscule,\n - une lettre majuscule,\n - un chiffre,\n - au moins un caractère spécial {'#$^+=!*()@%&'}, \n - pas d'espace",
        title: 'Mot de passe'
      },
      passwordConfirmation: {
        title: 'Confirmation du mot de passe',
        description: 'Confirmation du mot de passe'
      },
      newPassword: {
        description:
          "Mot de passe de 8 à 255 caractères, utilisant :\n - au moins une lettre minuscule,\n - une lettre majuscule,\n - un chiffre,\n - au moins un caractère spécial {'(#$^+=!*()@%&)'}, \n - pas d'espace",
        title: 'Nouveau mot de passe'
      },
      newPasswordConfirmation: {
        title: 'Confirmation du nouveau mot de passe',
        description: 'Confirmation du mot de passe'
      },
      role: {
        title: "Le rôle de l'utilisateur"
      },
      username: {
        description:
          "Nom d'utilisateur de 3 à 255 caractères, utilisant :\n- lettres minuscules/majuscules et chiffres\n- aucun caractère spécial à part -._\n- pas d'espace",
        title: "Nom d'utilisateur"
      }
    },
    idp: {
      columns: {
        type: 'Type',
        name: 'Name',
        label: 'Label'
      },
      errors: {
        existingIdp: "L'IdP {{idp_name}} existe déjà."
      },
      pending: 'Enregistrement de la configuration IdP en cours.',
      rejected: "Impossible d'enregistrer la configuration IdP : {{reason}}.",
      resolved: 'Configuration IdP enregistrée.',
      template: {
        ldapInformations: 'Informations du LDAP',
        samlInformations: 'informations du SAML',
        ldap_address: {
          description: "Ce paramètre contient le protocole LDAP, le nom ou l'adresse IP du serveur et son port.",
          title: 'Nom ou adresse IP (+ Port)'
        },
        entity_id: {
          description: "Identifiant de l'entité du fournisseur d'identité (généralement une URL)",
          title: 'Id IdP'
        },
        single_sign_on_service: {
          title: 'URL IdP utilisée pour la connexion',
          description: "URL cible du fournisseur d'identité où le message de demande d'authentification sera envoyé"
        },
        single_logout_service: {
          title: 'URL IdP utilisée pour la déconnexion',
          description: "URL de destination où la demande de déconnexion du fournisseur d'identité sera envoyée"
        },
        cert_fingerprint: {
          title: 'Certificat IdP',
          description: "Certificat public du fournisseur d'identité"
        },
        sign_authn_request: {
          title: "Signer la demande d'authentification",
          description: "Détermine si la demande d'authentification doit être signée"
        },
        sign_logout_request: {
          title: 'Signer la demande de déconnexion',
          description: 'Détermine si la demande de déconnexion doit être signée'
        },
        sp_public_cert: {
          title: 'Certificat public du SP',
          description: 'Certificat public du fournisseur de services'
        },
        sp_private_cert: {
          title: 'Certificat privé du SP',
          description: 'Certificat privé du fournisseur de services'
        },
        idp_type: {
          title: 'Type IdP',
          description: "Le type du fournisseur d'identité"
        },
        idp_name: {
          title: 'Nom',
          description:
            "Ce champ est utilisé pour spécifier le nom unique du fournisseur d'identité. Il ne peut contenir que des caractères alphanumériques et les caractères suivants : _.-"
        },
        idp_label: {
          title: 'Étiquette',
          description: "Ce champ est utilisé pour spécifier une étiquette conviviale du fournisseur d'identité"
        },
        autoAddUsers: {
          description:
            'Cette case à cocher détermine si les utilisateurs doivent être créés automatiquement avec les rôles choisis',
          title: 'Ajouter des utilisateurs automatiquement'
        },
        baseDn: {
          description: 'Ce champ spécifie le DN de la recherche de sous-nœud à partir duquel commencer.',
          title: 'DN de base'
        },
        bindDn: {
          description:
            "DN facultatif (Distinguished Name) à utiliser lors de la recherche LDAP. S'il est vide, les identifiants de l'utilisateur qui essaie de se connecter seront utilisés.",
          title: 'Lier DN'
        },
        bindPassword: {
          description:
            "Mot de passe facultatif à utiliser lors de la recherche LDAP. S'il est vide, les identifiants de l'utilisateur qui essaie de se connecter seront utilisés.",
          title: 'Mot de passe de liaison'
        },
        userFilter: {
          description: 'Filtre qui sera utilisé pour rechercher les utilisateurs LDAP',
          title: 'Filtre utilisateur'
        },
        searchFilter: {
          description: "Filtre qui sera utilisé pour rechercher le nom d'utilisateur lors de la demande LDAP",
          title: 'Filtre de recherche'
        },
        columns: {
          address: 'Nom ou adresse IP',
          baseDN: 'DN de base',
          domain: 'Domaine',
          group: 'Groupe',
          useSSL: 'Utiliser SSL'
        },
        domain: {
          description: 'Ce paramètre contient le domaine LDAP.',
          title: 'Domaine'
        },
        form: {
          password: 'Mot de passe',
          testLogin: 'Test de connexion LDAP',
          username: "Nom d'utilisateur LDAP"
        },
        group: {
          description: 'Ce champ détermine le groupe LDAP.',
          title: 'Groupe'
        },
        headerLabel: {
          add: 'Ajouter IdP'
        },
        roles: {
          description: 'Mettre à jour les rôles des utilisateurs avec les nouveaux rôles édités',
          label: 'Mettre à jour les rôles des utilisateurs avec les nouveaux rôles édités!',
          title: 'Rôles'
        },
        testConfig: 'Test de configuration',
        testServer: 'Test du serveur',
        validateConfig: 'Valider la configuration',
        useSsl: {
          description: "Cette case à cocher détermine l'utilisation de SSL.",
          title: 'Utiliser SSL'
        },
        view: {
          addNewConfig: 'Ajouter une nouvelle configuration IdP',
          clickToTest: 'Test du serveur'
        }
      },
      spMetadata: {
        spMetadata: 'Métadonnées du fournisseur de services',
        refreshMetadata: 'Rafraîchir les métadonnées du fournisseur de services',
        redirectUri: {
          description: "URI du fournisseur de services pour configurer le fournisseur d'identité",
          title: 'URI de redirection'
        },
        downloadSpMetadata: 'Télécharger les métadonnées SP',
        copyToClipboard: "Copier l'URI de redirection dans le presse-papiers",
        error:
          'Impossible de récupérer les métadonnées SP. Veuillez vérifier que la configuration ci-dessus est valide.'
      },
      user: {
        name: {
          autocomplete: "nom d'utilisateur",
          title: "Nom d'utilisateur LDAP"
        },
        password: {
          autocomplete: 'mot de passe',
          new: 'nouveau-mot-de-passe',
          title: 'Mot de passe LDAP'
        }
      },
      roleMapping: {
        defaultRoles: 'Rôles par défaut',
        mappers: 'Mappages',
        default: {
          title: 'Comportement par défaut',
          question:
            "Quelle action prendre si les attributs du fournisseur d'identité ne correspondent à aucun mappage au moment de la connexion ?",
          denyAccess: "Refuser l'accès",
          rolesToAdd: 'Rôle(s) à ajouter',
          addDefaultRoles: 'Ajouter des rôles par défaut',
          oneRoleMandatory: 'Au moins un rôle est obligatoire'
        },
        mapper: {
          add: 'Ajouter un mappage',
          title: 'Mappage',
          type: {
            title: 'Type',
            direct: 'Direct',
            simple: 'Simple'
          },
          attributeName: "Nom de l'attribut",
          attributeNameFormat:
            "Le nom de l'attribut doit commencer par un caractère alphabétique.\n" +
            'Il ne peut contenir que des caractères alphanumériques et les caractères suivants : ._\\\n' +
            'Pour accéder à une propriété imbriquée, vous pouvez utiliser un point : chemin.vers.la.propriete_imbriquee\n' +
            'Pour accéder à une propriété avec un point dans son nom, vous pouvez utiliser des barres obliques inversées : chemin.vers.la.propriete_imbriquee\\.avec\\.point',
          attributeValue: "Valeur de l'attribut",
          rolesToAdd: 'Rôle(s) à ajouter',
          oneRoleMandatory: 'Au moins un rôle est obligatoire',
          addNew: 'Ajouter un nouveau mappage',
          edit: 'Modifier le mappage',
          confirmDelete: 'Êtes-vous sûr de vouloir supprimer ce mappage ?',
          mappersWarning:
            "Vous devez définir le champ 'Filtre utilisateur' dans les détails LDAP pour que les mappages fonctionnent."
        }
      }
    },
    main: {
      general: 'Général',
      roles: 'Rôles',
      actions: 'Actions',
      logOut: 'Déconnexion',
      noFoundRole: '{{id}} non défini',
      sessionDeactivation: 'Désactiver le timeout de la session',
      confirmCurrentSession: 'Votre session restera active indéfiniment. Continuer ?',
      confirmUserSession: 'User session restera active indéfiniment. Continuer ?',
      passwordHeader: 'Mot de passe',
      submit: 'Soumettre',
      view: {
        role: 'Rôle',
        username: "Nom d'utilisateur",
        oldPassword: 'Ancien mot de passe',
        changePassword: 'Nouveau mot de passe',
        pendingPasswordChange: 'Changement de mot de passe en attente'
      },
      create: {
        addNewUser: 'Ajouter un utilisateur',
        userAlreadyExists: "L'utilisateur existe déjà",
        updatePwdWarning: "L'utilisateur devra mettre à jour le mot de passe lors de la première connexion;\n",
        cantCreateUser: "Impossible de créer l'utilisateur, il y a des erreurs dans le formulaire"
      },
      edit: {
        details: 'Détails',
        rolesMapping: 'Rôles',
        forceChangePassword: "Forcer l'utilisateur à changer de mot de passe lors de la prochaine connexion",
        passwordExpiration: "Le mot de passe n'expire jamais"
      }
    },
    roles: {
      addRoles: 'Ajouter des rôles',
      addActions: {
        description: 'Sélectionnez les actions que vous souhaitez ajouter à ce rôle',
        columns: {
          action: 'Action',
          label: 'Libellé',
          description: 'Description'
        }
      },
      addOtherActions: "Ajouter d'autres actions",
      actionsTabName: 'Actions disponibles',
      descriptionTitle: 'Description',
      headerLabel: 'Ajouter un rôle',
      labelTitle: 'Étiquette',
      name: 'Rôles',
      nameError: "Le nom doit correspondre au modèle alphanumérique ou ' * '.",
      nameTitle: 'Nom',
      prefixError: 'Le préfixe doit contenir entre {{min}} et {{max}} caractères alphabétiques.',
      prefixTitle: 'Préfixe',
      roleApplicableTabName: 'Applicable aux rôles',
      roleExists: 'Un rôle avec un tel préfixe ET un tel nom existe déjà',
      rolesTabName: 'Rôles disponibles',
      textTitle: 'Titre',
      view: {
        basicMode: 'Mode basique',
        description: 'Description',
        expertMode: 'Mode expert',
        label: 'Étiquette',
        modeTitle: 'En mode export, afficher tous les rôles',
        title: 'Rôle'
      }
    },
    sessions: {
      view: {
        username: "Nom d'utilisateur",
        idp_name: 'IdP',
        ip: 'IP',
        started_date: 'Date de début',
        expiration_date: 'Date de fin',
        deleteSession: 'Êtes-vous sûr de vouloir supprimer cette session ?'
      }
    },
    configuration: {
      logoutSettings: {
        title: 'Configuration',
        invalidCurrentUserDeactivationPeriod: 'La période de désactivation doit être comprise entre -1 et 3600',
        invalidPasswordMinimumLength: 'La longueur minimale du mot de passe doit être supérieure à 10',
        invalidCurrentMaxSuccessiveFailedLogin:
          'Le nombre maximal de tentatives de connexion successives doit être compris entre 1 et 10',
        idleTimeout: {
          title: "Temps d'inactivité",
          description: "le temps maximum d'inactivité de la connexion utilisateur"
        },
        sessionTimeout: {
          title: 'Durée de session',
          description: 'durée maximale de la session'
        },
        errorMessage: "Le temps d'inactivité doit être inférieur ou égal à la durée maximale de session",
        preferences: {
          pending: 'Mise à jour de la configuration en cours',
          resolved: 'Configuration mise à jour',
          rejected: 'Impossible de mettre à jour la configuration'
        },
        passwordPolicy: {
          pending: 'Mise à jour de la politique de mot de passe en cours',
          resolved: 'Politique de mot de passe mise à jour',
          rejected: 'Impossible de mettre à jour la politique de mot de passe'
        },
        maxSuccessiveFailedLogin: {
          title: 'Nombre maximal de tentatives de connexion successives ayant échoué',
          description: 'Nombre maximal de tentatives de connexion successives ayant échoué'
        },
        userDeactivation: {
          title: 'Activer la désactivation des utilisateurs',
          description: 'Activer la désactivation des utilisateurs'
        },
        forceChangePassword: {
          title: 'Forcer tous les utilisateurs à changer leur mot de passe.',
          description: 'Forcer tous les utilisateurs à changer leur mot de passe.'
        },
        userDeactivationPeriod: {
          title: "Période de désactivation de l'utilisateur (en secondes)",
          description: "Période (en secondes) pendant laquelle l'utilisateur est désactivé"
        },
        noAdminMessage: 'Seuls les administrateurs sont autorisés à mettre à jour cette configuration.',
        pwdPolicy: {
          title: 'Politique de mot de passe'
        },
        pwdExpiration: {
          title: 'Expiration du mot de passe',
          description: "Expiration du mot de passe en jours, (-1) s'il n'expire jamais"
        },
        pwdLength: {
          title: 'Longueur minimum du mot de passe',
          description: 'Longueur minimum du mot de passe'
        }
      },
      backupRestore: {
        main: {
          create: "Créer un fichier de sauvegarde de l'application",
          label: 'Sauvegarde / Restauration des utilisateurs',
          restore: "Restaurer un fichier de sauvegarde de l'application"
        },
        backup: {
          title: 'Sauvegarde des utilisateurs',
          titleCard: 'Télécharger un fichier de sauvegarde des utilisateurs',
          template: {
            saveLocally: {
              title: 'Enregistrer localement'
            },
            save: {
              title: 'Sauvegarder'
            }
          },
          buttonLabels: {
            save: 'Sauvegarder',
            saving: 'Sauvegarde en cours',
            saved: 'Sauvegarde effectuée',
            cannotSave: 'Impossible de sauvegarder'
          }
        },
        restore: {
          title: 'Restaurer les utilisateurs',
          titleCard: "Restaurer l'application à partir d'un fichier de sauvegarde",
          buttonLabels: {
            restore: 'Restaurer les utilisateurs',
            restoring: 'Restauration des utilisateurs en cours...',
            restored: 'Utilisateurs restaurés',
            cannotRestore: 'Impossible de restaurer les utilisateurs'
          },
          locally: 'Charger localement',
          errors: {
            fileToBig:
              "Le fichier est trop volumineux, même compressé : les données ne peuvent pas être envoyées pour restaurer le serveur d'alarme."
          },
          returnWarning: '(avertissement : {{warn}})',
          warningMessage: `Attention !
      Cette action va restaurer l'application avec une configuration archivée
      et des impacts possibles sur les opérations.`,
          confirmationMessage: 'Êtes-vous sûr de vouloir restaurer le serveur d"alarme ?'
        }
      }
    }
  }
}
