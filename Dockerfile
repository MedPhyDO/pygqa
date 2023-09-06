FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN env 

## ----------------------------------------------------------------
## Install Packages 
## ----------------------------------------------------------------
RUN apt update && apt install -y curl locales-all build-essential mc libpango-1.0-0 libpangoft2-1.0-0 tk gsfonts fonts-noto poppler-utils libpoppler-cpp-dev pkg-config cmake && rm -rf /var/lib/apt/lists/*

## ----------------------------------------------------------------
## Add custom Microsoft repository and install database driver 
## ----------------------------------------------------------------
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev mssql-tools
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc
RUN /bin/bash -c "source ~/.bashrc"

## ----------------------------------------------------------------
## Install python packages
## ----------------------------------------------------------------
RUN python3 -m pip install --upgrade pip

COPY ./requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt
 
## ----------------------------------------------------------------
## Copy files into container
## ----------------------------------------------------------------
WORKDIR /pygqa
COPY ./ ./

## ----------------------------------------------------------------
## install resources and copy odbc config
## ----------------------------------------------------------------
RUN python ./install-resources.py

# copy webfont to system for pdf creation
COPY --chmod=644 ./resources/vendor/fonts/materialdesignicons-webfont.ttf /usr/share/fonts/truetype/materialdesignicons_webfont.ttf
RUN fc-cache -v

COPY ./config/odbc.ini /etc/odbc.ini

ENV MPLCONFIGDIR="/tmp" 

## ----------------------------------------------------------------
## set port and start python, not used on network_mode: "host" 
## ----------------------------------------------------------------
#EXPOSE 5000

CMD ["python", "./pygqa.py" ] 
