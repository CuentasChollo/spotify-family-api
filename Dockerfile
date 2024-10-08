FROM public.ecr.aws/lambda/python@sha256:bf65727dd64fa8cbe9ada6a6c29a3fa4f248c635599e770366f8ac21eef36630 as build

RUN dnf install -y unzip && \
    curl -Lo "/tmp/chromedriver-linux64.zip" "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.105/linux64/chromedriver-linux64.zip" && \
    curl -Lo "/tmp/chrome-linux64.zip" "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.105/linux64/chrome-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/ && \
    unzip /tmp/chrome-linux64.zip -d /opt/

FROM public.ecr.aws/lambda/python@sha256:bf65727dd64fa8cbe9ada6a6c29a3fa4f248c635599e770366f8ac21eef36630
RUN dnf install -y atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm
RUN pip install selenium==4.19.0
COPY --from=build /opt/chrome-linux64 /opt/chrome
COPY --from=build /opt/chromedriver-linux64 /opt/

# Install necessary software
RUN dnf install -y wget xorg-x11-server-Xvfb

RUN python -m pip install ffmpeg

RUN pip install ffmpeg-python

# This is for inscribing the current url into the exception images to debug
RUN pip install pillow

# For requesting Spotify user information through Spotify's API
RUN pip install requests

RUN python -m pip install selenium-recaptcha-solver
RUN python -m pip install selenium-stealth
RUN python -m pip install fake_useragent
RUN python -m pip install ffprobe-python

# Install python-dotenv
RUN pip install python-dotenv

# Install BeautifulSoup
RUN python -m pip install beautifulsoup4

# Install dependencies for models.py
RUN pip install sqlalchemy

RUN pip install psycopg2-binary

# Copy your function code
COPY ./src /var/task/src
COPY ./local /var/task/local
COPY ./scripts /var/task/scripts
COPY ./models.py /var/task/

# Set the CMD to your handler (adjust the path if necessary)
CMD ["src.lambda_functions.add_family_client.add_family_client"]
