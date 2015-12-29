FROM python:2.7

# By setting the PORT environment var to 8000, nginx will listen on that port
ENV PORT 8000


# Install `build-essential`, `libmemcache` (headers), `ruby`, `gifsicle`, and
# `nodejs`
# We need ruby to compile our nginx config, libmemcache to compile connect,
# node to compile static assets, and gifsicle to resize animated gifs
# The node build script runs `apt-get update`, saving us that step
RUN curl -sL https://deb.nodesource.com/setup_5.x | bash - && \
    apt-get install -y nodejs build-essential libmemcached-dev ruby gifsicle && \
    apt-get clean


# Install `grunt` and `bower`, command-line node packages which handle
# dependency management and tasks such as compilation
RUN npm install -g bower grunt-cli


# Create a script called "proclaunch" that will let you launch a line from the
# heroku 'Procfile' by running "proclaunch {process}". So to run the "web"
# process just run "proclaunch web"
RUN printf '#!/bin/bash\ncd /app/ && eval "$(grep -i "^$1: " /app/Procfile | awk -F'\'': '\'' '\''{print $2}'\'')"' > /bin/proclaunch && \
    chmod +x /bin/proclaunch


# Move to the '/app' folder, where all of connect's files will live
RUN mkdir /app
WORKDIR /app


# Install 2 buildpacks

# nginx-buildpack: This will proxy gunicorn (the python http server) behind
# nginx, significantly speeding up and improving scalability of connect.
RUN git clone https://github.com/ryandotsmith/nginx-buildpack.git nginx-buildpack && \
    cd nginx-buildpack && \
    git checkout 005ca0374e3cf61a29fb0f9041a7315677af1972 && \
    STACK=cedar-14 bash bin/compile '/app' && \
    cd .. && rm -r nginx-buildpack


# pgbouncer buildpack: By default each request to connect will open a new
# connection to the postgresql database. Instead of relying on django's built-
# in persistent database connections, we can run pgbouncer locally and make
# those per-request connections lightning-fast, while limiting the connections
# to our database to one-per-container.
RUN git clone https://github.com/ofa/heroku-buildpack-pgbouncer.git pgbouncer-buildpack && \
    cd pgbouncer-buildpack && \
    git checkout cb5656d70991e98a1bf3f55a66b843939e3384e1 && \
    STACK=cedar-14 bash bin/compile '/app' && \
    cd .. && rm -r pgbouncer-buildpack


# Install node packages. This can be slow, so caching it is useful.
ADD package.json /app/package.json
RUN npm install


# We run pip as root so that python packages are available for all (and thus
# we can skip worrying about virtualenv.)
# Because we're adding requirements.txt separately Docker is smart and will
# cache this entire step until you change requirements.txt (or clear the cache)
ADD *requirements.txt /app/
RUN pip install -r requirements.txt


# Install bower packages. Change this file to break the built-in cache.
ADD bower.json /app/bower.json
RUN bower install --allow-root


# Add the Connect app to the `/app/` folder. This step will likely prevent the
# rest of the build from being cached. So any part of this build process that
# rarely changes should be above this line.
ADD . /app/


# Drop down into a local user. From here on out we'll only run things in /app/
# as the user 'appuser'
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser


# Compile frontend assets. Remember, you can set the environment variable
# `CONNECT_APP` to have this step run the compile step for a specific private
# version of connect.
RUN grunt

# We tell nginix to serve on port 8000, so we'll need this port exposed
EXPOSE 8000
