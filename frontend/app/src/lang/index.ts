import cathodicLangUs from '@ateme/cathodic-ui/src/lang/en-US'
import cathodicLangFr from '@ateme/cathodic-ui/src/lang/fr-FR'
import { LangMessagesType } from '@ateme/cathodic-ui/src/services/I18nNext'
import userManagementLangUs from './en-US'
import userManagementLangFr from './fr-FR'
const enList = ['en', 'en-US', 'en-EG', 'en-AU', 'en-GB', 'en-CA', 'en-NZ', 'en-IE', 'en-ZA', 'en-JM', 'en-BZ', 'en-TT']
const frList = ['fr', 'fr-BE', 'fr-CA', 'fr-FR', 'fr-LU', 'fr-MC', 'fr-CH']
/**
 * ui-components internationalization messages.
 * format : in camel case.
 */
/**
 * @description Internationalization messages for i18Next
 */
export default {
  ...enList.reduce((acc: LangMessagesType, key) => {
    acc[key] = {
      translation: {
        ...cathodicLangUs.translation,
        ...userManagementLangUs
      }
    }
    return acc
  }, {} as LangMessagesType),
  ...frList.reduce((acc: LangMessagesType, key) => {
    acc[key] = {
      translation: {
        ...cathodicLangFr.translation,
        ...userManagementLangFr
      }
    }
    return acc
  }, {} as LangMessagesType)
}
