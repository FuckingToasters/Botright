import random
import re

import numpy as np
import scipy.interpolate
import httpx

from .hcaptcha_challenger import (DIR_CHALLENGE, DIR_MODEL, PATH_OBJECTS_YAML, ArmorCaptcha)

class hCaptcha:
    captcha_token = ""

    def smooth_out_mouse(captcha_points):
        # Get the Captcha X- and Y-Coordinates
        x_coordinates, y_coordinates = [_[0] for _ in captcha_points], [_[1] for _ in captcha_points]
        # Fixxing https://github.com/Vinyzu/DiscordGenerator/issues/3 by adding an extra point
        # (Its two points for real basicly you click an correct image two times again)
        if len(x_coordinates) <= 2:
            random_index = random.choice(range(len(x_coordinates)))
            x1, x2 = x_coordinates[random_index] + 1, x_coordinates[random_index] - 1
            x_coordinates.extend([x1, x2])
            y1, y2 = y_coordinates[random_index] + 1, y_coordinates[random_index] - 1
            y_coordinates.extend([y1, y2])
        # Devide x and y coordinates into two arrays
        x, y = np.array(x_coordinates), np.array(y_coordinates)
        # i dont even know, copy pasted from this so https://stackoverflow.com/a/47361677/16523207
        x_new = np.linspace(x.min(), x.max(), 200)
        f = scipy.interpolate.interp1d(x, y, kind='quadratic')
        y_new = f(x_new)
        # Converting NpArrays to lists
        y_new = y_new.tolist()
        x_new = x_new.tolist()
        # Randomize Points to emulate human mouse wobblyness
        x_new = [random.uniform(x-random.randint(5, 20)/10, x+random.randint(5, 20)/10) for x in x_new]
        y_new = [random.uniform(y-random.randint(5, 20)/10, y+random.randint(5, 20)/10) for y in y_new]

        return x_new, y_new, x_coordinates, y_coordinates

    async def log_captcha(page):
        async def check_json(route, request):
            await route.continue_()
            try:
                response = await request.response()
                await response.finished()
                json = await response.json()
                if json.get("generated_pass_UUID"):
                    hCaptcha.captcha_token = json.get("generated_pass_UUID")
            except Exception:
                pass

        await page.route("https://hcaptcha.com/checkcaptcha/**", check_json)

    async def mock_captcha(page, rqdata):
        async def mock_json(route, request):
            payload = {**request.post_data_json, "rqdata": rqdata} if rqdata else request.post_data_json
            response = await page.request.post(request.url, form=payload, headers=request.headers)
            json = await response.json()

            if json.get("generated_pass_UUID"):
                    hCaptcha.captcha_token = json.get("generated_pass_UUID")
            await route.fulfill(response=response)

        await page.route("https://hcaptcha.com/getcaptcha/**", mock_json)

        
    
    async def captcha_solver(self):
        # Getting Challenge Frame
        try:
            captcha_frames = self.page.frame_locator("//iframe[contains(@title,'content')]")
            captcha_frame = captcha_frames.first
            
        except Exception:
            return hCaptcha.captcha_token

        # Getting Question and Label of the Captcha
        try:
            question_locator = captcha_frame.locator("//h2[@class='prompt-text']") # maybe sometimes timeout error?
            question = await question_locator.text_content()
 
        except playwright._impl._api_types.TimeoutError: 
            self.logger.error("Timeout exceeded while selecting hidden element, restarting Browser...")
            for _ in range(2): await self.close()
            return
            # return False
            await self.close()
 
        except Exception as e:
            if hCaptcha.captcha_token: return Captcha.captcha_token
            self.logger.error("Captcha Question didnt load")
            for _ in range(2): await self.close()
            return
            # return False
            

        label = re.split(r"containing a", question)[-1][1:].strip() if "containing" in question else question
        label = label.replace(".", "")

        # Initializing ArmorCaptcha
        challenger = ArmorCaptcha(dir_workspace=DIR_CHALLENGE, dir_model=DIR_MODEL, lang='en', debug=True,path_objects_yaml=PATH_OBJECTS_YAML, onnx_prefix="yolov5s6")
        # Getting Lavel and Model from AI
        challenger.label = label
        model = challenger.switch_solution()  # DIR_MODEL, None
        # More Realistic Human Behaviour
        await page.wait_for_timeout(2000)
        # Get All of the Images
        image_locator = captcha_frame.locator("//div[@class='task-image']")
        # Define Captcha Points and Used Captha points
        captcha_points, used_captcha_points = [], []
        
        # Getting Random Coordinate from Image if Image is Correct
        for i in range(await image_locator.count()):
            element = image_locator.nth(i)
            sub_element = element.locator('[class="image-wrapper"]').locator('[class="image"]')
            style = await sub_element.get_attribute("style")
            image_url = style.split('url("')[1].split('"')[0]

            data = httpx.get(image_url).content
            # Getting Result from AI and appending it to list
            try:
                result = model.solution(img_stream=data, label=challenger.label_alias[label])
            except KeyError as e:
                raise KeyError(f"AI doesnt support captcha of type {label} yet.")

            if result:
                # Getting X,Y, Width and Height of Captcha Image if its True/Valid
                boundings = await element.bounding_box()
                x, y, width, height = boundings.values()
                # Clicking on random Location in the Picture for better MotionData
                while True:
                    random_x, random_y = random.randint(int(x), int(x + width)), random.randint(int(y), int(y + height))
                    if random_x not in [_[0] for _ in captcha_points]:
                        captcha_points.append([random_x, random_y])
                        break

        # Ignore
        if not captcha_points:
            return False
        # Get Coodinates of Smooth out mouse line
        x_new, y_new, x_coordinates, y_coordinates = hCaptcha.smooth_out_mouse(captcha_points)

        # Method to insert the Original Captcha Points into the Curve Points
        zipped_rounded_points = [list(a) for a in zip([int(x) for x in x_new], [int(y) for y in y_new])]
        for point in captcha_points:
            # Check if Point is not in the Curve Points
            if point not in zipped_rounded_points:
                best_index, best_difference = 0, 1000
                for i, difference_point in enumerate(zipped_rounded_points):
                    # Check Difference between Point and DifferencePoint
                    x_difference = point[0] - difference_point[0]
                    y_difference = point[1] - difference_point[1]
                    # Make Negative Number Positive with the Abs() Function
                    difference = abs(x_difference) + abs(y_difference)
                    # Check if DifferencePoint is newest to given Point
                    if difference < best_difference:
                        best_index, best_difference = i, difference
                # Insert the Point at the best calculated Point
                x_new.insert(best_index+1, point[0])
                y_new.insert(best_index+1, point[1])

        for x, y in zip(x_new, y_new):
            x, y = int(x), int(y)
            # Check if coordinate is in the captcha_point (If yes, click it)
            # Also Check if the captcha was already clicked
            if any(x == int(_) for _ in x_coordinates) and x not in used_captcha_points:
                await page.mouse.click(x, y, humanly=False)
                # Append Coordinate to Used Captcha Points
                used_captcha_points.append(x)
                await page.wait_for_timeout(random.randint(5, 20))
            else:
                await page.mouse.move(x, y, humanly=False)
                await page.wait_for_timeout(random.randint(3, 10))

        await page.wait_for_timeout(600)
        # Clicking Submit Button
        submit_button = captcha_frame.locator("//div[@class='button-submit button']").first
        await submit_button.click()
        # Checking if Captcha was Bypassed
        for _ in range(1000):
            if hCaptcha.captcha_token:
                return hCaptcha.captcha_token
            else:
                await page.wait_for_timeout(10)

        # If Captcha Token wasnt fetched redo Captcha
        return await hCaptcha.solve_captcha(page, checkbox)

    async def solve_hcaptcha(page, rqdata=None):
        hCaptcha.captcha_token = None
        # Logging Captcha Token
        await hCaptcha.log_captcha(page)
        # Mocking Captcha Request
        await hCaptcha.mock_captcha(page, rqdata)
        # Clicking Captcha Checkbox
        try:
            checkbox = page.frame_locator('[title *= "hCaptcha security challenge"]').locator('[id="checkbox"]')
            await checkbox.click()
        except Exception:
            raise RuntimeError("Captcha didnt load")
        # Clicking Checkbox
        await page.wait_for_timeout(2000)

        return await hCaptcha.solve_captcha(page, checkbox)

    async def get_hcaptcha(browser, sitekey="00000000-0000-0000-0000-000000000000", rqdata=None):
        page = await browser.new_page()
        await page.goto(f"https://accounts.hcaptcha.com/demo?sitekey={sitekey}")
        return await page.solve_hcaptcha(rqdata=rqdata)
