# Audible OPDS Firebase

A simple firebase-functions based app to create an OPDS feed from a users audible library.

## Setup

Setup python and install dependencies
```
brew install ffmpeg
cd functions
python3 -m venv venv
./pip.sh
```

If you want to run tests, they are in nodejs (sorry):

Setup your .env.local in `functions/`
```
API_KEY=LOCAL_API_KEY
ENVIRONEMENT=dev
BUCKET_NAME=my-bucket-name
```

Now install node dependencies and run the tests.
```
cd test
npm install
mkdir bin
cp $(which ffmpeg) bin/
cd ..
./test.sh
```

## Deploy

```
firebase deploy --only functions
```
