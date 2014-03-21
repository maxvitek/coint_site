from django.test import TestCase
from celery import addtask


# Celery tests
class TestWorker(TestCase):
    def test_worker_function(self):
        """
        Tests that the celery worker is functioning
        """
        test_result = addtask.delay(2, 2).get()
        expected_result = 4

        self.assertEqual(test_result, expected_result)