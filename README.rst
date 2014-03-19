Coint
=====

This is going to be a web app demonstration
of a cointegration-based pairs strategy.  We
will use Google Finance's intraday data to
simulate algorithmic trades, starting with
$10,000 each morning and reporting on
performance throughout the day.

Our numerical methods will employ Python's
NumPy, SciPy, Pandas.  The app will be a
Django app.  Celery workers will be used to
asynchronously crunch the numbers.  RabbitMQ
will be the task queue.  Heroku is where we'll
put all of this.  We'll use drone to keep us on
the free tier.

Despite the sound of all that, I want it to
be simple.