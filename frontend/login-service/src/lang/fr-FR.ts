export default {
  auth: {
    login: {
      form: {
        logged: 'Connecté',
        loggingIn: 'Connexion en cours...',
        login: 'Connexion',
        serverError: 'Erreur du serveur, veuillez réessayer plus tard',
        timeRemaining: 'Utilisateur désactivé pendant {{seconds}} secondes après trop de tentatives',
        wrongUserNameOrPassword: "Nom d'utilisateur ou mot de passe incorrect",
        accessDenied: 'Accès refusé'
      }
    },
    errors: {
      required: 'Ce champ est obligatoire',
      invalidFormat: 'Format invalide',
      passwordsMatch: 'Les mots de passe ne correspondent pas.',
      wrongFormat: 'Format de mot de passe non valide.',
      wrongPassword: 'Mot de passe incorrect.',
      wrongPasswordDescription: 'Votre ancien mot de passe est incorrect. Veuillez réessayer.',
      unauthorized: 'Accès non autorisé. Redirection vers la page de connexion.',
      forbidden: 'Accès interdit.',
      passwordMustBeDifferent: "Le nouveau mot de passe doit être différent de l'ancien."
    },
    ping: {
      message: {
        communicate: "La connexion de l'utilisateur ne peut pas aller plus loin.",
        pleaseWait: "Le service de gestion des utilisateurs n'est pas encore prêt."
      }
    },
    password: {
      description:
        'Mot de passe de {{min_length}} à 255 caractères, utilisant:\n' +
        'Au moins une lettre minuscule\n' +
        'Une lettre majuscule\n' +
        'Un chiffre\n' +
        "Au moins un caractère spécial {'#$^+=!*()@%&'}\n" +
        "Pas d'espace",
      title: 'Mot de passe'
    },
    username: "Nom d'utilisateur",
    oldPassword: 'Ancien mot de passe',
    changePassword: 'Nouveau mot de passe',
    passwordConfirmation: 'Confirmation du mot de passe',
    submitButton: {
      submit: 'Confirmer',
      submitting: 'Confirmation...',
      submitted: 'Confirmé',
      failure: 'Mot de passe incorrect'
    },
    submitLabels: {
      pending: 'Mise à jour du mot de passe...',
      resolved: 'Mot de passe mis à jour',
      rejected: 'Mot de passe incorrect, veuillez rééssayer'
    },
    tmpPwd: 'Vous avez reçu un mot de passe temporaire, modifiez le mot de passe pour continuer',
    pwdExpired: 'Votre mot de passe est expiré, modifiez le mot de passe pour continuer'
  }
}
