from playwright.sync_api import sync_playwright
import time, pickle, os

urls = {
    "login": "https://www.knowitallninja.com/login/?redirect_to=%2Fdashboard%2F",
    "targetCourse": "https://www.knowitallninja.com/dashboard/courses/exploring-user-interface-design-principles/"
}

def main():
    login = ["", ""]
    with open("login") as f:
        login[0] = f.readline().strip()
        login[1] = f.readline().strip()

    print(f"Using {login[0]}:{'*'*len(login[1])}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
        executable_path="/home/rajaa/.cache/ms-playwright/chromium-1161/chrome-linux/chrome")
        page = browser.new_page()
        page.goto(urls.get("login"), wait_until="networkidle")

        page.fill("#user_login", login[0])
        page.fill("#user_pass", login[1])

        with page.expect_navigation():
            page.click('button[name="submit"]')

        page.wait_for_load_state('networkidle')

        page.goto(urls.get("targetCourse"), wait_until="networkidle")

        links = page.eval_on_selector_all(
            "a", "elements => elements.map(el => el.href)"
        )

        courses = [l for l in links if l.startswith("https://www.knowitallninja.com/dashboard/courses/")]

        for course in courses:
            page.goto(course, wait_until="networkidle")

            links = page.eval_on_selector_all(
                "a", "elements => elements.map(el => el.href)"
            )
            print(f"{'-'*10} DOING COURSE {course} {'-'*10}")
            for link in links:
                if "https://www.knowitallninja.com/dashboard/lessons/" in link:
                    quizLink = link.replace("lessons", "quizzes")
                    print(f"Navigating to {quizLink}")

                    page.goto(quizLink, wait_until="networkidle")

                    if page.title() == 'Page not found - KnowItAll Ninja':
                            print("Failed, skipping to next")
                            continue
                        
                    page.click("input[name='startQuiz']")
                    
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

                            data.push(answers);
                        });

                        return data;
                        }
                        """)
                        x = "fjqo"
                        with open(f"answers/{quizFileName}.pckl", "wb") as f:
                            pickle.dump(answers, f)
                        page.goto(quizLink, wait_until="networkidle")

                    else:
                        answers = []
                        print("Using memorised answers")
                        with open(f"answers/{quizFileName}.pckl", "rb") as f:
                            answers = pickle.load(f)

                    #print(answers)

                    #page.click("input[name='startQuiz']")
                    for i in answers:
                        time.sleep(1)
                        for j in i:
                            print(f"clicking {j}")
                            page.evaluate("""
                                (targetText) => {
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

                                    // Try to click matching label
                                    const labels = Array.from(document.querySelectorAll('label'));
                                    for (const label of labels) {
                                        if (label.textContent.includes(targetText) && isVisible(label)) {
                                            label.click();
                                            return;
                                        }
                                    }
                                }
                            """, j)
                        page.evaluate("""
                            () => {
                                const el = document.querySelector('[name="next"]');
                                if (el) el.click();
                            }
                        """)

                    page.click("input[name='endQuizSummary']")
                    page.wait_for_load_state('networkidle')
                    time.sleep(2)

        browser.close()

if __name__ == "__main__":
    main()