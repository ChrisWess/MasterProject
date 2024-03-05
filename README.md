# ObjeXplain WebApp

This project is part of a master thesis of the University of Hamburg. The ObjeXplain is an image annotation tool for describing details of objects.

## Author
- [@Christoph Wessarges](https://github.com/ChrisWess)


## Acknowledgements
This Web-App uses a neural network architecture in the backend to annotate digital images with a description for each object that is well visible in an image.  
 - [The original neural network architecture that the auto annotation model is based on (written in Tensorflow/Keras)](https://github.com/sandareka/CCNN)


## How to run the app

### Backend
First you will need to be able to run the backend:
 - move to your base `ObjeXplain`-directory (where this README should be located).
 - Install Python3 dependencies: `pip install -r requirements.txt`.
 - Download the models weights `ccnn-cub-data.mar` from [this page](https://github.com/todo).
 - Extract the `model*.pt`, create a new directory `./app/autoxplain/base/model_saves` and place the .pt file in that directory.
 - If running locally: start your mongodb instance (in case of issues: check if the configuration in `config.py` points to your mongodb address).
 - start the backend with the flask server `python3 application.py`.
 - look [here](https://github.com/todo) if you still have any trouble setting the backend up.

### Frontend
If the backend is running, the application is ready to be started. 
 - Move to the `ObjeXplain/objexplain-frontend`-directory.
 - Run `npm install` to install all required packages.
 - Run `npm start` to start the development server to test out the React Frontend locally.
 - For more info regarding React JS, see the `README.md` in `ObjeXplain/objexplain-frontend`.

## Demo

