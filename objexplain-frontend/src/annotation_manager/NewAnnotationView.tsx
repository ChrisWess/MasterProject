import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {FC, useEffect, useRef, useState} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setDoc, setImgUrl} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {ImageDocument} from "../api/models/imgdoc";
import {loadDocImage, loadProject} from "../document/ProjectIDocPage";
import {cropImage, loadDoc} from "../object_annotator/ObjectPage";
import NewAnnotationControlPanel from "./NewAnnotationControl";
import AnnotationWriter from "./AnnotationWriter";
import ConceptBuilderView from "./ConceptBuilderView";
import {setObject, setObjectIdx, setObjectLabel} from "../reducers/objectSlice";
import {setTitle} from "../reducers/appBarSlice";
import AnnotationInspector from "./AnnotationInspector";
import {Label} from "../api/models/label";
import {fetchLabel} from "../object_annotator/LabelSelector";
import {getMappedLabel} from "../object_annotator/ObjectControl";
import AlertMessage from "../components/AlertMessage";


const AnnotationCreateView: FC = () => {
    const {projectName, docId, objIdx} = useParams();
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const modeId: number = useSelector((state: any) => state.newAnno.modeId);

    let objIntIdx = objIdx ? parseInt(objIdx) : undefined;

    useEffect(() => {
        if (!projectName) {
            navigate('/notfound404')
        } else if (!project || project.title != projectName) {
            loadProject(projectName).then(projectData => projectData ?
                dispatch(setProject(projectData.result)) :
                navigate('/notfound404'))
        }
        if (!docId) {
            navigate('/notfound404')
        } else if (!idoc || idoc._id != docId) {
            loadDoc(docId).then(idocData => {
                if (idocData) {
                    dispatch(setDoc(idocData.result));
                    loadDocImage(docId).then(file => {
                        file && dispatch(setImgUrl(file))
                    });
                } else {
                    navigate('/notfound404')
                }
            })
        }
        context.setControlPanel(<NewAnnotationControlPanel/>)
    }, []);

    useEffect(() => {
        if (imgUrl && idoc?.objects) {
            if (objIntIdx !== undefined && objIntIdx >= 0 && objIntIdx < idoc.objects.length) {
                dispatch(setObjectIdx(objIntIdx));
                dispatch(setTitle(`Object ${objIntIdx + 1} of ${idoc.name}`));
                let obj = idoc.objects[objIntIdx];
                dispatch(setObject(obj));
                if (!objectLabel || objectLabel._id !== obj.labelId) {
                    let mappedLabel = undefined;
                    if (labelsMap) {
                        mappedLabel = getMappedLabel(labelsMap, obj.labelId);
                    }
                    if (mappedLabel) {
                        dispatch(setObjectLabel(mappedLabel))
                    } else {
                        fetchLabel(obj.labelId).then(data => data && dispatch(setObjectLabel(data.result)))
                    }
                }
                let newWidth = obj.brx - obj.tlx
                let newHeight = obj.bry - obj.tly
                cropImage(canvasRef, imgUrl, obj.tlx, obj.tly, newWidth, newHeight)
            } else {
                navigate('/notfound404')
            }
        }
    }, [idoc, imgUrl, objIntIdx, labelsMap]);

    return (
        <Box height='100%'>
            <Box height='59%'
                 sx={{
                     p: 2, bgcolor: 'rgba(50, 50, 255, 0.08)',
                     border: '2px solid',
                     borderColor: 'divider',
                     position: 'relative'
                 }}>
                <Box ref={imgContainer} height='93%' sx={{
                    position: 'absolute', display: 'block',
                    left: '50%', transform: 'translateX(-50%)'
                }}>
                    {<canvas ref={canvasRef} style={{height: '100%'}}/>}
                </Box>
            </Box>
            <Box height='38%'
                 sx={{
                     display: 'flex',
                     justifyContent: 'center',
                     alignItems: 'center',
                     bgcolor: 'rgba(50, 50, 255, 0.08)',
                     fontSize: '20px',
                     border: '2px solid',
                     borderColor: 'divider',
                     my: 1
                 }}>
                <Box>
                    <AnnotationWriter index={0} value={modeId}/>
                    <ConceptBuilderView index={1} value={modeId} setAlertContent={setAlertContent}
                                        setAlertSeverity={setAlertSeverity}/>
                    <AnnotationInspector index={2} value={modeId}/>
                </Box>
            </Box>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default AnnotationCreateView
