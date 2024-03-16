import React from 'react';
import './App.css';
import UserDashboard from "./dashboard/UserDashboard";
import {createBrowserRouter, createRoutesFromElements, Navigate, Route, RouterProvider} from "react-router-dom";
import NotFound from "./utils/NotFound";
import TestPage from "./components/TestPage";
import RootLayout from "./layouts/RootLayout";
import ProjectMainPage from "./project_main/ProjectMainPage";
import ProjectLayout from "./layouts/ProjectLayout";
import {loadProject} from "./project_main/ProjectLoader";
import ProjectIDocPage from "./document/ProjectIDocPage";
import {loadIDoc} from "./document/DocumentLoader";
import ObjectPage from "./object_annotator/ObjectPage";
import NewObjectPage from "./object_annotator/NewObjectPage";
import AnnotationView from "./annotation_manager/AnnotationView";
import AnnotationCreateView from "./annotation_manager/NewAnnotationView";


const router = createBrowserRouter(
    createRoutesFromElements(
        <Route path="/" element={<RootLayout/>}>
            <Route index element={<Navigate to="/dashboard" replace/>}/>
            <Route path="project" element={<ProjectLayout/>}>
                <Route index element={<Navigate to="/dashboard" replace/>}/>
                <Route path=":projectName" element={<ProjectMainPage/>} loader={loadProject}/>
                <Route path=":projectName/idoc/:docId" element={<ProjectIDocPage/>} loader={loadIDoc}/>
                <Route path=":projectName/idoc/:docId/:objIdx" element={<ObjectPage/>}/>
                <Route path=":projectName/idoc/:docId/newObj" element={<NewObjectPage/>}/>
                <Route path=":projectName/idoc/:docId/:objIdx/:annoIdx" element={<AnnotationView/>}/>
                <Route path=":projectName/idoc/:docId/:objIdx/newAnno" element={<AnnotationCreateView/>}/>
            </Route>
            <Route path="test" element={<TestPage/>}/>
            <Route path="dashboard" element={<UserDashboard/>}/>
            {/* Using path="*"" means "match anything", so this route
                  acts like a catch-all for URLs that we don't have explicit
                  routes for. */}
            <Route path="*" element={<NotFound/>}/>
        </Route>
    )
)


function App() {
    return (
        <RouterProvider router={router}/>
    );
}

export default App;
