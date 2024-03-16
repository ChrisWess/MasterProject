import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import {configureStore} from "@reduxjs/toolkit";
import {Provider} from "react-redux";
import userReducer from "./reducers/userSlice"
import appBarReducer from "./reducers/appBarSlice"
import mainPageReducer from "./reducers/mainPageSlice"
import docReducer from "./reducers/idocSlice"
import objectPageReducer from "./reducers/objectSlice"
import newObjectPageReducer from "./reducers/objectCreateSlice"
import annotationPageReducer from "./reducers/annotationSlice";
import newAnnotationPageReducer from "./reducers/annotationCreateSlice";


const store = configureStore({
    reducer: {
        user: userReducer,
        appBar: appBarReducer,
        mainPage: mainPageReducer,
        iDoc: docReducer,
        object: objectPageReducer,
        newObj: newObjectPageReducer,
        annotation: annotationPageReducer,
        newAnno: newAnnotationPageReducer,
    }
})

const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
);

root.render(
    <React.StrictMode>
        <Provider store={store}>
            <App/>
        </Provider>
    </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
