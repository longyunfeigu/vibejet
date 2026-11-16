# language: en
Feature: Diet — Today and this week

  # Source: docs/product/requirements.md (食衡 PRD) — not implemented yet.
  # Activation gate: grep -rn "summary" backend/api/routes frontend/src/features

  @DIET-RVW-001 @smoke
  Scenario Outline: Asking about today returns a system-computed summary and records nothing
    Given a diet user with a "1600" kcal target and "960" kcal eaten today
    When I send "<question>"
    Then the reply should include a summary of target "1600", eaten "960" and remaining "640" with macronutrients
    And the summary should match the daily totals API
    And no new meal should be recorded

    Examples:
      | question |
      | 今天还能吃多少 |
      | 我今天好像吃多了 |

  @DIET-RVW-002 @regression
  Scenario: Today's summary follows every add, edit, delete and undo
    Given a diet user with a "1600" kcal target
    When I record a "500" kcal meal
    Then today's summary should show "500" eaten
    When I change that meal to "600" kcal
    Then today's summary should show "600" eaten
    When I delete that meal
    Then today's summary should show "0" eaten
    When I undo the deletion
    Then today's summary should show "600" eaten

  @DIET-RVW-003 @regression
  Scenario Outline: Going over the target is stated calmly with a weekly view
    Given a diet user with a "1600" kcal target and "<eaten>" kcal eaten today
    When I send "今天还能吃多少"
    Then the reply should state an excess of "<excess>" kcal with a weekly suggestion
    And the reply should not contain "失败" or "警告"
    And no number should be shown in a warning colour

    Examples:
      | eaten | excess |
      | 1601 | 1 |
      | 2030 | 430 |

  @DIET-RVW-004 @negative
  Scenario: Eating exactly the target is not an excess
    Given a diet user with a "1600" kcal target and "1600" kcal eaten today
    When I send "今天还能吃多少"
    Then today's summary should show "0" remaining
    And the reply should not mention an excess

  @DIET-RVW-005 @regression
  Scenario Outline: The weekly average counts only days with records
    Given a diet user with a "1600" kcal target
    And meals on "<days>" of the last 7 days
    When I send "这周怎么样"
    Then the weekly average should be the mean of the recorded days only
    And the reply should mention "<missing>" missing days

    Examples:
      | days | missing |
      | 7 | 0 |
      | 6 | 1 |
      | 1 | 6 |

  @DIET-RVW-006 @negative
  Scenario: A week with no records shows no average
    Given a diet user with a "1600" kcal target and no meals this week
    When I send "这周怎么样"
    Then the reply should say there are no records this week
    And the reply should contain no calorie numbers

  @DIET-RVW-007 @regression
  Scenario Outline: The weekly review appears at the top after Sunday 20:00
    Given a diet user with meals on "6" days this week
    And the server time is "<time>" on Sunday
    When I open the chat page
    Then the weekly review should be "<shown>" at the top

    Examples:
      | time | shown |
      | 19:59 | not shown |
      | 20:00 | shown |

  @DIET-RVW-008 @regression
  Scenario: After weeks away only the latest weekly review is shown
    Given a diet user with meals over the last "3" weeks who has not opened the app
    And the server time is "21:00" on the third Sunday
    When I open the chat page
    Then exactly one weekly review for the latest week should be shown

  @DIET-RVW-009 @negative
  Scenario: Numbers in the weekly review come from the system, not the model
    Given a diet user whose Saturday was "430" kcal over the target
    And the model will write "999" kcal into the review text
    When the weekly review is generated
    Then the review should show "430" kcal for Saturday
    And the review should not show "999"

  @DIET-RVW-010 @regression @slow
  Scenario: A failed review is generated later without blocking logging
    Given a diet user with meals this week and the server time "20:30" on Sunday
    And the model will return an error
    When I open the chat page
    Then no weekly review and no error trace should be shown
    And I can still record "吃了两个苹果"
    When the model recovers and I open the chat page again
    Then the weekly review should be shown

  @DIET-RVW-012 @negative
  Scenario: A user cannot see another user's summaries or reviews
    Given two diet users "A" and "B"
    And user "A" has meals and a weekly review this week
    When user "B" requests user "A"'s daily summary and weekly review
    Then every request should be answered as not found
