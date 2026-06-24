"""
This script is designed to do just enough tasks to be elligible for the daily rewards system on knowitallninja and claim them.
I suggest running this from cron daily on a server.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time, pickle, os, random, datetime, sys, json
from pydantic import BaseModel, Field, ConfigDict, field_validator

urls = {
    "login": "https://www.knowitallninja.com/login/?redirect_to=%2Fdashboard%2F",
    "targetCourse": "https://www.knowitallninja.com/dashboard/courses/exploring-user-interface-design-principles/"
}

delaySettings = {
    "timeBetweenQuestions": 20,
    "timeBetweenQuizzes": 25,
    "delayJitter" : 5
}

speedRunMode = True
speedRunFactor = 10

if speedRunMode:
    delaySettings = {
        "timeBetweenQuestions": max(0, delaySettings.get("timeBetweenQuestions") - speedRunFactor),
        "timeBetweenQuizzes": max(0, delaySettings.get("timeBetweenQuizzes") - speedRunFactor),
        "delayJitter" : 5
    }

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Login(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    password: str

if not os.path.isdir("answers"):
    os.mkdir("answers")

def main():
    with open("login.json", "r") as f:
        login_json = json.load(f)

    login = Login.model_validate(login_json)

    if login.username == "i didnt read the readme and never changed this":
        print(f"Pretty funny username you got there, '{login.username}'")
        print(f"Make sure to put your login details in {os.getcwd()}/login.json as the bot needs to login as you to act on your behalf.")
        if input("Would you like to populate the login file now? (Y/n)").lower().strip() != "n":
            logindetails = {
                "username": input("Username/email: ").strip(),
                "password": input("password: ").strip()
            }
            with open("login.json", "w") as f:
                json.dump(logindetails, f, indent=2)
            login = Login.model_validate(logindetails)
        else:
            print("Exiting...")
            return

    print(f"Using {login.username}:{'*'*len(login.password)}")

    startTime = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.goto(urls.get("login"), wait_until="networkidle")

        page.fill("#user_login", login.username)
        page.fill("#user_pass", login.password)

        with page.expect_navigation():
            page.click('button[name="submit"]')

        page.wait_for_load_state('networkidle')

        page.goto(urls.get("targetCourse"), wait_until="networkidle")

        links = page.eval_on_selector_all(
            "a", "elements => elements.map(el => el.href)"
        )

        courses = [l for l in links if l.startswith("https://www.knowitallninja.com/dashboard/courses/")]

        for course in courses:
            try:
                page.goto(course, wait_until="networkidle")
                failureCount = 0

                links = page.eval_on_selector_all(
                    "a", "elements => elements.map(el => el.href)"
                )
                print(bcolors.OKGREEN, f"{'-'*10} DOING COURSE {course} {'-'*10}", bcolors.ENDC)
                for link in links:
                    if "https://www.knowitallninja.com/dashboard/lessons/" in link:
                        if failureCount >= 5:
                            continue #skip inf until counter resets on enxt course

                        page.goto("https://www.knowitallninja.com/dashboard/", wait_until="networkidle")
                        elements = page.query_selector_all(".claim-points")
                        if len(elements) == 2:
                            for i in elements:
                                i.click()
                                sys.exit(0)
                        
                        quizLink = link.replace("lessons", "quizzes")
                        #quizLink = "https://www.knowitallninja.com/dashboard/quizzes/skill-level-demographics/" # for specifc testing
                        print(f"Navigating to {quizLink}")

                        page.goto(quizLink, wait_until="networkidle")

                        if page.title() == 'Page not found - KnowItAll Ninja':
                            print(bcolors.FAIL, "Failed, skipping to next", bcolors.ENDC)
                            failureCount += 1
                            continue
                            
                        try:
                            page.click("input[name='startQuiz']")
                        except PlaywrightTimeoutError:
                            print(bcolors.FAIL, "Timeout: 'start Quiz' button not found, skipping this quiz.", bcolors.ENDC)
                            failureCount += 1
                            continue 
                        
                        quizFileName = quizLink.split("/")[len(quizLink.split("/")) - 2]
                        if not os.path.exists(f"answers/{quizFileName}.pckl"):
                            page.evaluate("""
                                () => {
                                    const el = document.querySelector('[name="endQuizSummary"]');
                                    if (el) el.click();
                                }
                            """)

                            page.wait_for_load_state('networkidle')

                            page.click("input[name='reShowQuestion']")

                            answers = page.evaluate("""
                            () => {
                            const ol = document.querySelector('ol.wpProQuiz_list');
                            if (!ol) return [];

                            const data = [];

                            ol.querySelectorAll('li').forEach(li => {
                            const questionContent = li.querySelector('div.kian-quiz-question-content');
                            if (!questionContent) return;

                            const questionFieldset = questionContent.querySelector('fieldset.wpProQuiz_question');
                            if (!questionFieldset) return;

                            const questionList = questionFieldset.querySelector('div.wpProQuiz_questionList');
                            if (!questionList) return;

                            const answerDivs = questionList.querySelectorAll('div.wpProQuiz_answerCorrectIncomplete');

                            // Collect text or any other info you want from each answer div
                            const answers = [];
                            answerDivs.forEach(div => {
                                answers.push(div.innerText.trim());
                            });

                            if (answers.length === 0) {
                                const clozeSpans = li.querySelectorAll('.ld-quiz__cloze-results--correct-answer');
                                clozeSpans.forEach(span => {
                                    const content = span.textContent.trim();
                                    if (content.startsWith('(') && content.endsWith(')')) {
                                        const opts = content.slice(1, -1).split(',');
                                        if (opts.length > 0) answers.push(opts[0]); // pick first valid synonym
                                    } else if (content.length > 0) {
                                        answers.push(content);
                                    }
                                });
                            }

                            data.push(answers);
                            });

                            return data;
                            }
                            """)
                            with open(f"answers/{quizFileName}.pckl", "wb") as f:
                                pickle.dump(answers, f)
                            page.goto(quizLink, wait_until="networkidle")
                            page.click("input[name='startQuiz']")
                        else:
                            answers = []
                            print("Using memorised answers")
                            with open(f"answers/{quizFileName}.pckl", "rb") as f:
                                answers = pickle.load(f)

                        #print(answers)

                        #page.click("input[name='startQuiz']")
                        for i in answers:
                            time.sleep(delaySettings.get("timeBetweenQuestions") + random.randint(-delaySettings.get("delayJitter"), -delaySettings.get("delayJitter")))
                            if i != []:
                                for j in i:
                                    #print(f"\rclicking {j}\r", end="")
                                    page.evaluate("""
                                        async (targetText) => {
                                            const isVisible = (el) => {
                                                if (!el) return false;
                                                const style = window.getComputedStyle(el);
                                                const rect = el.getBoundingClientRect();
                                                return (
                                                    style.display !== 'none' &&
                                                    style.visibility !== 'hidden' &&
                                                    style.opacity !== '0' &&
                                                    rect.width > 0 &&
                                                    rect.height > 0
                                                );
                                            };

                                            const highlight = (el) => {
                                                const originalBorder = el.style.border;
                                                el.style.border = '3px solid red';
                                                setTimeout(() => {
                                                    el.style.border = originalBorder;
                                                }, 3000);
                                            };

                                            const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

                                            // Try to click matching label
                                            const labels = Array.from(document.querySelectorAll('label'));
                                            for (const label of labels) {
                                                if (label.textContent.includes(targetText) && isVisible(label)) {
                                                    label.click();
                                                    return;
                                                } else if (label.querySelector('input[type="text"]')) {

                                                    const tb = label.querySelector('input[type="text"]');
                                                    if (tb && !isVisible(tb)) {
                                                        delay(1000);
                                                    }
                                                    if (isVisible(tb) && !tb.getAttribute('data-filled')) {
                                                        tb.focus();
                                                        highlight(tb);
                                                        tb.value = targetText;
                                                        tb.dispatchEvent(new Event('input', { bubbles: true }));
                                                        delay(500);
                                                        tb.setAttribute('data-filled', 'true');
                                                        return;
                                                    }

                                                }
                                            }
                                        }
                                    """, j)
                            else:
                                page.evaluate("""
                                    () => {
                                        const isVisible = (el) => {
                                            if (!el) return false;
                                            const style = window.getComputedStyle(el);
                                            const rect = el.getBoundingClientRect();
                                            return (
                                                style.display !== 'none' &&
                                                style.visibility !== 'hidden' &&
                                                style.opacity !== '0' &&
                                                rect.width > 0 &&
                                                rect.height > 0
                                            );
                                        };

                                        //Last resort, maybe its a drag and drop
                                        const fieldsets = Array.from(document.querySelectorAll('fieldset'));
                                        for (const fieldset of fieldsets) {
                                            if (isVisible(fieldset)) {
                                                const draggableItems = Array.from(fieldset.querySelectorAll(".wpProQuiz_sortStringItem"));
                                                const locationItems = Array.from(fieldset.querySelectorAll('.wpProQuiz_questionListItem'));

                                                if (draggableItems.length && locationItems.length) {
                                                    for (let i = 0; i < Math.min(draggableItems.length, locationItems.length); i++) {
                                                        const dropZone = locationItems[draggableItems[i].getAttribute('data-pos')].querySelector('ul.wpProQuiz_maxtrixSortCriterion');
                                                        if (dropZone) {
                                                            console.log('Dropped child')
                                                            dropZone.appendChild(draggableItems[i]);
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                    }
                                """)
                            page.evaluate("""
                                () => {
                                    const el = document.querySelector('[name="next"]');
                                    if (el) el.click();
                                }
                            """)
                            #print("-"*10)

                        try:
                            page.click("input[name='endQuizSummary']")
                        except PlaywrightTimeoutError:
                            print(bcolors.FAIL, "Timeout: 'end Quiz' button not found, skipping this quiz.", bcolors.ENDC)
                            failureCount += 1
                            continue
                        page.wait_for_load_state('networkidle')
                        page.wait_for_selector(".kian-quiz-result-progress-percentage")
                        score = page.query_selector(".kian-quiz-result-progress-percentage").inner_text().removesuffix("%")
                        if (float(score)) != 100.00:
                            print(bcolors.WARNING, f"[!] Got percentage {score}% on {quizLink}", bcolors.ENDC)
                        time.sleep(delaySettings.get("timeBetweenQuizzes") + random.randint(-delaySettings.get("delayJitter"), -delaySettings.get("delayJitter")))
                        print("-"*20,f"Ran for {round(int(time.time() - startTime)/60, 2)}m current time {datetime.datetime.now()}", "-"*20)
            except:
                print(bcolors.FAIL, f"[!!!] Failed to do course {course}", bcolors.ENDC)    

        browser.close()

if __name__ == "__main__":
    main()