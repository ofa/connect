# Connect

### Local install
1. Install pip and virtualenv if you don't already have them:
	
		sudo easy_install pip virtualenv

2. Create a new virtualenv in the directory above connect. I have connect inside a directory called MessagesDemo, but you can make it whatever you want. Inside that directory:

		virtualenv --no-site-packages --distribute ./

3. Create a mysql database and user. In a mysql prompt:

		create database connect default character set utf8 collate utf8_unicode_ci;
		create user `connect`@`localhost` identified by 'bAk2Gastek';
    GRANT ALL ON connect to `connect`@`localhost`; 
		flush privileges;

4. Inside the same directory you created the virtualenv:

		source bin/activate

	(this activates the python virtual environment)

5. Install requirements

		cd connect
		pip install -r requirements.txt

6. (If you have problems with the MySQL Library) Create symlink to mysql

		sudo ln -s /usr/local/mysql/lib/libmysqlclient.18.dylib /usr/lib/libmysqlclient.18.dylib

7. Create an empty log file

		mkdir logs
		touch logs/debug.log

8. Initialize database

		python manage.py syncdb --noinput
		python manage.py migrate

9. Start the development server

		python manage.py runserver


## Notifications via Celery

Notifications are handled asynchronously using django-celery. If you want to receive email notifications, you have to run a celery daemon.

        ./manage.py celeryd -v 2 -B -s celery -E -l INFO

Non-local versions of the application should use rabbitmq as the celery broker. To enable this, get a rabbitmq server running and set the DJANGO_ENVIRONMENT env var to staging or production.

## Client-side dependencies: Bower & Grunt JS

Use `bower install` to update client-side components like Bento Box. Use '`bower list` to see what we have installed and if there are new versions.' If you add a new client side dependency, add it to `bower.json`. Make sure dependencies have version numbers so they can be easily installed 

To setup Grunt:

1. Install Node if you haven't yet.
2. Install Grunt Command Line tools globally (Note that installing grunt-cli does not install the Grunt task runner!):
	`npm install -g grunt-cli`
3. Install project dependencies with `npm install`.
4. Use `grunt --help` to list the tasks in the Gruntfile, or open up `Gruntfile.js` to make changes

## Regarding color-coding issues in Connect:

All issues-specific (and therefore color-coded) LESS in Connect should be handled with a loop. Detailed instructions are included in `_variables.less`

## Search

Haystack is configured to use elastic search as a search backend. To use search, [download elastic search](http://www.elasticsearch.org/), run the server (bin/elasticsearch -f) and then create an index (manage.py rebuild_index or manage.py update_index).

## API

API is supported using a basic-auth: 

```
$ python manage.py api_key user@foo.com create

API Key for "user": "8c83570b425d460cb47220a5627212009e1c07b9"

$ curl -X GET https://api-stag.herokuapp.com/api/groups/ -H 'Authorization: Token 8c83570b425d460cb47220a5627212009e1c07b9'
```

