import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {FC, useEffect, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setDoc, setImgUrl} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {ImageDocument} from "../api/models/imgdoc";
import {loadDocImage, loadProject} from "../document/ProjectIDocPage";
import {loadDoc} from "../object_annotator/ObjectPage";
import NewAnnotationControlPanel from "./NewAnnotationControl";


const AnnotationCreateView: FC = () => {
    const {projectName, docId, objIdx} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);

    let objIntIdx = objIdx ? parseInt(objIdx) : undefined;
    let objId = idoc?.objects && objIntIdx !== undefined ? idoc.objects[objIntIdx]._id : undefined

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
                </Box>
            </Box>
        </Box>
    )
}

export default AnnotationCreateView
