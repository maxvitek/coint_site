from selenium import webdriver
import unittest


class HomePage(unittest.TestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def test(self):
        # user goes to homepage
        self.browser.get('http://localhost:8000')

        # sees nice title!
        self.assertIn('Cointegration', self.browser.title)


if __name__ == '__main__':
    unittest.main()