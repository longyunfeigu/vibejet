# language: en
Feature: Diet — Profile and daily target

  # Source: docs/product/requirements.md (食衡 PRD) — not implemented yet.
  # Activation gate: grep -rn "profile" backend/api/routes frontend/src/features

  @DIET-PRF-001 @smoke
  Scenario: A new user without a profile is sent to the profile form
    Given a new diet user without a profile
    When I open the home page
    Then I should be on the profile page
    And the profile form should show the fields "性别, 身高, 体重, 年龄, 活动量, 目标体重, 减重速度"

  @DIET-PRF-002 @regression
  Scenario Outline: Filling in the profile gives a daily target with its breakdown, and editing the profile recalculates it
    Given a new diet user without a profile
    When I submit the profile "<profile>"
    Then the daily target should equal the expected value for "<profile>"
    And the breakdown should show basal metabolism, daily expenditure and daily deficit
    When I lower my weight by "2" kg and save
    Then the daily target should be recalculated for the new weight
    And after reloading the page the profile and target should be unchanged

    Examples:
      | profile |
      | female-28-165-60-light-55 |
      | male-35-178-85-moderate-75 |

  @DIET-PRF-003 @regression
  Scenario Outline: Each weight-loss speed sets the matching daily deficit
    Given a diet user with the standard profile
    When I choose the weight-loss speed "<speed>" kg per week
    Then the daily deficit should be "<deficit>" kcal
    And the daily target should equal daily expenditure minus "<deficit>" kcal
    And after reloading the page the speed "<speed>" should stay selected

    Examples:
      | speed | deficit |
      | 0.25 | 275 |
      | 0.5 | 550 |
      | 0.75 | 825 |

  @DIET-PRF-004 @regression
  Scenario Outline: Profile values on the edge of the allowed range are accepted
    Given a new diet user without a profile
    When I submit the profile with "<field>" set to "<value>"
    Then the profile should be saved
    And the profile should show "<field>" as "<value>"

    Examples:
      | field | value |
      | height | 100 |
      | height | 250 |
      | weight | 30 |
      | weight | 300 |
      | age | 18 |
      | age | 100 |

  @DIET-PRF-005 @negative
  Scenario Outline: Out-of-range or malformed profile values are rejected
    Given a new diet user without a profile
    When I submit the profile with "<field>" set to "<value>"
    Then the field "<field>" should show an error
    And I should still be on the profile page
    And the user should still have no saved profile

    Examples:
      | field | value |
      | height | 99 |
      | height | 251 |
      | weight | 29.9 |
      | weight | 300.1 |
      | age | 101 |
      | height |  |
      | weight | 六十 |

  @DIET-PRF-006 @negative
  Scenario: A user under 18 cannot create a profile
    Given a new diet user without a profile
    When I submit the profile with "age" set to "17"
    Then I should see the under-18 notice
    And the user should still have no saved profile

  @DIET-PRF-007 @regression
  Scenario Outline: A target below the safe minimum needs a second confirmation
    Given a new diet user without a profile
    When I submit the profile "<profile>"
    Then I should see the low-target risk warning
    When I cancel the warning
    Then the user should still have no saved profile
    When I submit the profile "<profile>" again and confirm the warning
    Then the profile should be saved with the low daily target

    Examples:
      | profile |
      | female-low-target |
      | male-low-target |

  @DIET-PRF-008 @regression
  Scenario Outline: The safe-minimum warning starts exactly one kcal below the limit
    Given a diet user with the standard profile and sex "<sex>"
    When I set the daily target manually to "<target>" kcal
    Then the low-target risk warning should be "<warned>"

    Examples:
      | sex | target | warned |
      | female | 1200 | not shown |
      | female | 1199 | shown |
      | male | 1500 | not shown |
      | male | 1499 | shown |

  @DIET-PRF-009 @regression
  Scenario: A manual daily target survives profile edits while the formula value stays visible
    Given a diet user with the standard profile
    When I set the daily target manually to "1600" kcal
    Then the daily target should be "1600" kcal with the formula suggestion shown beside it
    When I change my weight to "58" kg and save
    Then the daily target should still be "1600" kcal
    And the formula suggestion should be recalculated for "58" kg

  @DIET-PRF-010 @regression
  Scenario: Reaching the goal weight offers maintenance mode
    Given a diet user with the standard profile
    And a 7-day weight history averaging "55.0" kg
    When I open the home page
    Then I should be offered maintenance mode or a new goal
    When I choose maintenance mode
    Then the daily deficit should be "0" kcal
    And after reloading the page the goal-reached offer should not appear again

  @DIET-PRF-011 @negative
  Scenario: No goal-reached offer while the 7-day average is still above the goal
    Given a diet user with the standard profile
    And a 7-day weight history averaging "55.1" kg
    When I open the home page
    Then I should not be offered maintenance mode

  @DIET-PRF-012 @regression
  Scenario: Deleting the account needs confirmation and removes every piece of the user's data
    Given a diet user with the standard profile and some conversations, meals, weights and a custom food
    When I start deleting my account and cancel
    Then my profile should still be readable
    When I delete my account and confirm
    Then I should be signed out on the login page
    And signing in with the deleted account should fail
    And the old session should be rejected by the profile API
    And the database should hold no profile, conversation, meal, weight, custom food or model usage rows for the deleted user

  @DIET-PRF-013 @negative
  Scenario: A user cannot read or change another user's profile
    Given two diet users "A" and "B" with profiles
    When user "B" requests user "A"'s profile
    Then the request should be answered as not found
    When user "B" tries to update user "A"'s profile
    Then the request should be answered as not found
    And user "A"'s profile should be unchanged
