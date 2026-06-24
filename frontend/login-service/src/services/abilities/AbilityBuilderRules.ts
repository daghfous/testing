import { AbilityBuilder, createMongoAbility, MongoAbility } from '@casl/ability'

import { ALL, UserRightEnum } from './constants/common'
import { defaultRules } from './defaultRules'

const { VIEW, USE } = UserRightEnum

//TODO: Migration check this file
class AbilityBuilderRules {
  private abilityBuilder: AbilityBuilder<MongoAbility>
  private ability: MongoAbility | undefined

  constructor() {
    this.abilityBuilder = new AbilityBuilder(createMongoAbility)
    this.ability = undefined

    this.abilityBuilder.cannot(VIEW, ALL)
    this.abilityBuilder.cannot(USE, ALL)
  }
  setUserRight(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    access: any,
    //eslint-disable-next-line @typescript-eslint/no-explicit-any
    projectBuild: Array<(access: any, builder: AbilityBuilder<MongoAbility>) => void> = []
  ) {
    if (access) {
      this.abilityBuilder.cannot(VIEW, ALL)
      this.abilityBuilder.cannot(USE, ALL)

      // Common
      defaultRules.forEach(build => build(access, this.abilityBuilder))
      // Project
      projectBuild.forEach(build => build(access, this.abilityBuilder))

      this.ability = this.abilityBuilder.build()
    }
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getRules(): any[] {
    return this.abilityBuilder.rules
  }

  getBuilder(): AbilityBuilder<MongoAbility> {
    return this.abilityBuilder
  }

  getAbility(): MongoAbility | undefined {
    return this.ability
  }

  canView(right: string): boolean {
    return this.ability ? this.ability.can(VIEW, right) : false
  }
}

const builder: AbilityBuilderRules = new AbilityBuilderRules()
export const getSingletonBuilder: () => AbilityBuilderRules = () => builder
export default AbilityBuilderRules
