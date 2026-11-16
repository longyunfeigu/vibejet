# language: en
Feature: Diet — Log a meal in one sentence

  # Source: docs/product/requirements.md (食衡 PRD) — not implemented yet.
  # Activation gate: grep -rn "meal" backend/api/routes frontend/src/features

  @DIET-MEAL-001 @smoke
  Scenario: The chat page is ready for a sentence and shows the food search entry
    Given a diet user with the standard profile
    When I open the chat page
    Then the message input should be ready
    And the "搜索食物库" entry should be visible

  @DIET-MEAL-002 @regression
  Scenario: A sentence becomes a card that only counts after confirmation
    Given a diet user with the standard profile
    When I send "中午吃了黄焖鸡米饭，饭吃了一半"
    Then a meal card should list "黄焖鸡 1 份 300 克" and "米饭 半碗 75 克" with calories from the food database
    And today's eaten calories should still be "0"
    When I confirm the card
    Then the reply should state the remaining calories for today
    And today's lunch should hold "2" entries
    And after reloading the page today's meals and totals should be unchanged

  @DIET-MEAL-003 @regression
  Scenario Outline: Everyday portion words are converted with the food database unit weights
    Given a diet user with the standard profile
    When I send "<sentence>"
    Then the meal card should list "<items>"
    And every card item should be priced from the food database

    Examples:
      | sentence | items |
      | 早上一杯美式，一个肉包子 | 美式咖啡 1 杯 350 毫升; 肉包 1 个 100 克 |
      | 下午一杯奶茶，大杯半糖 | 奶茶 1 大杯 700 毫升 半糖 |
      | 吃了两个苹果 | 苹果 2 个 400 克 |
      | 麻辣烫大概 300 克 | 麻辣烫 300 克 |
      | 两瓶啤酒 | 啤酒 2 瓶 1000 毫升 |

  @DIET-MEAL-004 @negative
  Scenario: Calories invented by the model are ignored
    Given a diet user with the standard profile
    And the model will claim "9999" kcal for "吃了两个苹果"
    When I send "吃了两个苹果" and confirm the card
    Then the saved meal calories should come from the food database
    And no saved value should be "9999"

  @DIET-MEAL-005 @negative
  Scenario: An unconfirmed card is never counted
    Given a diet user with the standard profile
    When I send "吃了两个苹果" without confirming
    And I send "两瓶啤酒" and confirm the card
    Then today's meals should only contain "啤酒"

  @DIET-MEAL-006 @regression
  Scenario Outline: A vague meal triggers one question with options before any card
    Given a diet user with the standard profile
    When I send "<sentence>"
    Then the reply should ask exactly one question about "<topic>" with clickable options
    And today's eaten calories should still be "0"
    When I pick the first option
    Then a meal card should appear
    When I confirm the card
    Then today's meals should hold the picked food

    Examples:
      | sentence | topic |
      | 晚上吃火锅 | 吃了哪些 |
      | 三明治 | 哪一种 |
      | 一份鸡胸肉沙拉 | 份量 |

  @DIET-MEAL-007 @regression
  Scenario: Two uncertain items are asked about one at a time
    Given a diet user with the standard profile
    When I send "三明治和一杯奶茶"
    Then the reply should ask exactly one question
    When I pick the first option
    Then the reply should ask exactly one more question
    When I pick the first option
    Then a meal card should list "三明治" and "奶茶"

  @DIET-MEAL-008 @regression
  Scenario: Corrections before confirming update the same card
    Given a diet user with the standard profile
    When I send "中午吃了黄焖鸡米饭，饭吃了一半"
    And I send "饭吃完了"
    Then the card should show "米饭 1 碗 150 克" and still be unconfirmed
    When I send "不是黄焖鸡，是黄焖排骨"
    Then the card should show "黄焖排骨 1 份 300 克"
    When I confirm the card
    Then today's lunch should hold "黄焖排骨" and "米饭 1 碗"

  @DIET-MEAL-009 @regression
  Scenario: A correction after confirming replaces the original entry
    Given a diet user with the standard profile
    And a confirmed lunch of "黄焖鸡 1 份" and "米饭 半碗"
    When I send "饭吃完了"
    Then a revised card should appear
    And today's lunch should still show "米饭 半碗"
    When I confirm the revised card
    Then today's lunch should hold "2" entries with "米饭 1 碗"

  @DIET-MEAL-010 @negative
  Scenario: An unconfirmed revision leaves the original entry alone
    Given a diet user with the standard profile
    And a confirmed lunch of "黄焖鸡 1 份" and "米饭 半碗"
    When I send "饭吃完了" without confirming
    And I send "两瓶啤酒" and confirm the card
    Then today's lunch should still show "米饭 半碗"

  @DIET-MEAL-011 @regression
  Scenario: A food missing from the database must be matched before it can be saved
    Given a diet user with the standard profile
    When I send "中午吃了螺蛳粉炒年糕"
    Then the item "螺蛳粉炒年糕" should be marked as unmatched with suggestions and a create-custom-food option
    And the card cannot be confirmed yet
    When I pick the suggestion "炒年糕" and confirm the card
    Then today's lunch should hold "炒年糕"

  @DIET-MEAL-012 @regression
  Scenario: A custom food is saved and recognised next time
    Given a diet user with the standard profile
    When I send "午饭吃了妈妈做的卤肉饭 250 克"
    And I create the custom food "妈妈做的卤肉饭" with "180" kcal per 100 g
    And I confirm the card
    Then today's lunch should hold "妈妈做的卤肉饭" with "450" kcal
    When I send "午饭吃了妈妈做的卤肉饭 250 克" again
    Then the item should match my custom food without asking

  @DIET-MEAL-013 @negative
  Scenario: Custom foods are private to their owner
    Given two diet users "A" and "B"
    And user "A" has the custom food "妈妈做的卤肉饭"
    When user "B" searches the food database for "妈妈做的卤肉饭"
    Then user "B" should get no results
    And user "B" requesting user "A"'s custom food should be answered as not found

  @DIET-MEAL-014 @regression
  Scenario Outline: A sentence can back-fill yesterday's meal
    Given a diet user with the standard profile
    When I send "<sentence>" and confirm the card
    Then yesterday's "<meal>" should hold the food
    And today's eaten calories should still be "0"

    Examples:
      | sentence | meal |
      | 昨天晚饭忘记记了，吃的牛肉面 | 晚餐 |
      | 昨天宵夜一碗泡面 | 加餐 |

  @DIET-MEAL-015 @negative
  Scenario Outline: Back-filling is limited to the last 7 days including today
    Given a diet user with the standard profile
    When I send "<days> 天前的午饭吃了牛肉面"
    Then back-filling should be "<result>"

    Examples:
      | days | result |
      | 6 | allowed |
      | 7 | refused |

  @DIET-MEAL-016 @regression
  Scenario: "Same as yesterday" copies yesterday's meal after confirmation
    Given a diet user with the standard profile
    And yesterday's lunch of "黄焖鸡 1 份" and "米饭 半碗"
    When I send "午饭跟昨天一样"
    Then the meal card should list "黄焖鸡 1 份" and "米饭 半碗"
    When I confirm the card
    Then today's lunch should hold "黄焖鸡 1 份" and "米饭 半碗"

  @DIET-MEAL-017 @regression
  Scenario: Meals are grouped into days by the user's time zone
    Given a diet user in time zone "Asia/Shanghai" with the standard profile
    And a meal logged at "23:59" local time on day one and another at "00:01" local time on day two
    When I open the meal history
    Then each day should hold exactly its own meal and total

  @DIET-MEAL-018 @regression
  Scenario: Searching the food database records a meal without the model
    Given a diet user with the standard profile
    When I search the food database for "牛肉面" and record "1 碗"
    Then today's meals should hold "牛肉面 1 碗" priced from the food database
    And the model should not have been called

  @DIET-MEAL-019 @negative
  Scenario: An empty search offers to create a custom food
    Given a diet user with the standard profile
    When I search the food database for "不存在的食物"
    Then I should see no results and an option to create a custom food

  @DIET-MEAL-020 @regression @slow
  Scenario Outline: When the model fails the user can still record by search, keeping date and meal
    Given a diet user with the standard profile
    And yesterday's dinner is selected
    And the model will "<failure>"
    When I send "晚饭吃了牛肉面"
    Then within "10" seconds I should see that the AI is unavailable with a food search button
    And my sentence should be kept in the input history
    When I record "牛肉面 1 碗" from the food search
    Then yesterday's dinner should hold "牛肉面 1 碗"

    Examples:
      | failure |
      | time out |
      | return an error |
      | be unconfigured |

  @DIET-MEAL-021 @regression @slow
  Scenario: A slow but in-time model reply still produces a card
    Given a diet user with the standard profile
    And the model will reply after "9" seconds
    When I send "吃了两个苹果"
    Then a meal card should list "苹果 2 个"
    And no AI-unavailable message should be shown

  @DIET-MEAL-022 @negative
  Scenario Outline: Malformed model output is never saved
    Given a diet user with the standard profile
    And the model will return "<output>"
    When I send "吃了两个苹果"
    Then no confirmable card should appear
    And I should be offered a question or the food search
    And today's meals should be empty

    Examples:
      | output |
      | invalid structure |
      | negative portion |
      | missing food name |

  @DIET-MEAL-023 @negative
  Scenario Outline: Medical and off-topic questions are declined without recording
    Given a diet user with the standard profile
    When I send "<sentence>"
    Then the reply should say it only handles diet records
    And no meal card should appear
    And today's meals should be empty

    Examples:
      | sentence |
      | 糖尿病能吃西瓜吗 |
      | 帮我写一份周报 |

  @DIET-MEAL-024 @regression
  Scenario: Entries can be edited, deleted and restored with totals always in step
    Given a diet user with the standard profile
    And today's lunch of "黄焖鸡 300 克" and "米饭 75 克"
    When I change "米饭" to "150" grams
    Then today's total should include "米饭 150 克"
    When I delete "黄焖鸡"
    Then today's total should no longer include "黄焖鸡"
    When I undo the deletion
    Then today's lunch should hold "黄焖鸡 300 克" again with the total restored

  @DIET-MEAL-025 @negative
  Scenario Outline: Only entries from the last 7 days can be changed
    Given a diet user with the standard profile
    And a meal logged "<days>" days ago
    When I try to edit and delete that meal
    Then changing it should be "<result>"

    Examples:
      | days | result |
      | 6 | allowed |
      | 7 | refused |

  @DIET-MEAL-026 @negative
  Scenario Outline: Confirming the same card twice records it once
    Given a diet user with the standard profile
    When I send "吃了两个苹果"
    And I "<action>"
    Then today's meals should hold "苹果 2 个" exactly once

    Examples:
      | action |
      | double-click confirm |
      | confirm, reload and confirm again |

  @DIET-MEAL-027 @negative
  Scenario: A user cannot reach another user's conversations or meals
    Given two diet users "A" and "B"
    And user "A" has a conversation and a confirmed meal
    When user "B" reads, edits and deletes user "A"'s conversation and meal
    Then every request should be answered as not found
    And user "A"'s conversation and meal should be unchanged

  @DIET-MEAL-028 @negative
  Scenario: Model requests carry no identity and logs keep no raw sentences
    Given a diet user with the standard profile
    When I send "中午吃了黄焖鸡米饭，饭吃了一半"
    Then the request received by the model should not contain my user id, username or email
    And the backend log should not contain the sentence "中午吃了黄焖鸡米饭，饭吃了一半"

  @DIET-MEAL-029 @regression
  Scenario: Every model call is metered per user
    Given a diet user with the standard profile
    When I send "3" meal sentences
    Then my usage record should show "3" model calls with their usage summed

  @DIET-MEAL-030 @regression
  Scenario: The core logging flows work on a 375 px wide phone screen
    Given a diet user with the standard profile on a "375" px wide screen
    When I send "吃了两个苹果" and confirm the card
    And I record "牛肉面 1 碗" from the food search
    Then both meals should be recorded
    And the page should have no horizontal scroll

  @DIET-MEAL-031 @regression @slow
  Scenario: With the real model 90% of sentences reach a card within 3 seconds
    Given the pre-release environment uses the real model
    When I send the "100" evaluation sentences one by one
    Then the 90th percentile time to card should be at most "3" seconds
