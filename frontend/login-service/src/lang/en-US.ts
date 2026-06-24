export default {
  auth: {
    login: {
      form: {
        logged: 'Logged',
        loggingIn: 'Logging in...',
        login: 'Login',
        serverError: 'Server error, please try again later',
        timeRemaining: 'User disabled for {{seconds}} seconds after too many attempts',
        wrongUserNameOrPassword: 'Wrong username or password',
        accessDenied: 'Access denied'
      }
    },
    errors: {
      required: 'This field is required',
      invalidFormat: 'Invalid format',
      passwordsMatch: 'Passwords do not match.',
      wrongFormat: 'Not valid password format.',
      wrongPassword: 'Wrong password',
      wrongPasswordDescription: 'Your old password is incorrect. Please try again.',
      unauthorized: 'Access unauthorized. Redirect to login page.',
      forbidden: 'Access forbidden.',
      passwordMustBeDifferent: 'The new password must be different from the old one'
    },
    ping: {
      message: {
        communicate: 'User login cannot proceed further.',
        pleaseWait: 'The user management service is not yet ready.'
      }
    },
    username: 'Username',
    oldPassword: 'Old password',
    changePassword: 'Change password',
    passwordConfirmation: 'Password confirmation',
    password: {
      description:
        'Password from {{min_length}} to 255 characters long, using:\n' +
        'At least one lower case letter\n' +
        'One upper case letter\n' +
        'One digit\n' +
        "At least one special character {'(#$^+=!*()@%&)'}\n" +
        'No space',
      title: 'Password'
    },
    submitButton: {
      submit: 'Submit',
      submitting: 'Submitting...',
      submitted: 'Submitted',
      failure: "Can't update password"
    },
    submitLabels: {
      pending: 'Updating profile...',
      resolved: 'Profile updated',
      rejected: 'Incorrect profile, please retry'
    },
    tmpPwd: 'You have been granted a temporary password, edit password to continue',
    pwdExpired: 'Your password has expired, edit password to continue'
  }
}
