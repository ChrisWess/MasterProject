import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest} from "../api/requests";
import {FC, useEffect, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setTitle} from "../reducers/appBarSlice";
import {setProject} from "../reducers/mainPageSlice";
import {Button} from "@mui/material";
import {Label} from "../api/models/label";
import ObjectControlPanel from "./ObjectControl";
import {ImageDocument} from "../api/models/imgdoc";
import {setObject, setObjectIdx} from "../reducers/objectSlice";
import {setDoc, setImgUrl, setLabelMap} from "../reducers/idocSlice";
import {mapLabels} from "../document/DocControl";
import Tooltip from "@mui/material/Tooltip";
import {DetectedObject} from "../api/models/object";
import {loadDocImage, loadProject} from "../document/ProjectIDocPage";


export const cropImage = (canvasRef: any, imgUrl: string, newX: number, newY: number,
                          newWidth: number, newHeight: number) => {
    let canvas = canvasRef.current;
    if (imgUrl && canvas !== null) {
        //create an image object from the path
        const originalImage = new Image();
        originalImage.src = imgUrl;

        //initialize the canvas object
        const ctx = canvas.getContext('2d')!;

        //wait for the image to finish loading
        originalImage.addEventListener('load', function () {
            if (canvas) {
                //set the canvas size to the new width and height
                canvas.width = newWidth;
                canvas.height = newHeight;

                //draw the image
                ctx.drawImage(originalImage, newX, newY, newWidth, newHeight, 0, 0, newWidth, newHeight);
            }
        });
    }
}

export const loadDoc = async (docId: string) => {
    return await getRequest('idoc', docId)
}

const ObjectPage: FC = () => {
    const {projectName, docId, objIdx} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);

    // This page is only visible to Project Managers and Admins and shows all annotations of the users.
    // The Annotation View shows only the annotation of single user with all its details. An annotator
    // sees only his own annotation.

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
        context.setControlPanel(<ObjectControlPanel/>)
    }, []);

    useEffect(() => {
        if (!labelsMap) {
            mapLabels(idoc).then(lm => lm && dispatch(setLabelMap(lm)));
        }
    }, [idoc, labelsMap]);

    useEffect(() => {
        if (objIdx) {
            let idx = parseInt(objIdx);
            if (imgUrl && idoc && idoc.objects) {
                if (idx >= 0 && idx < idoc.objects.length) {
                    dispatch(setObjectIdx(idx));
                    dispatch(setTitle(`Object ${idx + 1} of ${idoc.name}`));
                    let obj = idoc.objects[idx];
                    dispatch(setObject(obj));
                    let newWidth = obj.brx - obj.tlx
                    let newHeight = obj.bry - obj.tly
                    cropImage(canvasRef, imgUrl, obj.tlx, obj.tly, newWidth, newHeight)
                } else {
                    navigate('/notfound404')
                }
            }
        } else {
            navigate('/notfound404')
        }
    }, [idoc, imgUrl]);

    // TODO: save user interaction as preferences and determine the best layout for a user with these stats

    return (
        <Box height='100%'>
            <Box height='94%'
                 sx={{
                     p: 2, bgcolor: 'rgba(50, 50, 255, 0.08)',
                     border: '2px solid',
                     borderColor: 'divider',
                     position: 'relative'
                 }}>
                <Box ref={imgContainer} height='96%' sx={{
                    position: 'absolute', display: 'block',
                    left: '50%', transform: 'translateX(-50%)'
                }}>
                    {imgUrl &&
                        <Tooltip title={`Bounding Box: ${[detObj?.tlx, detObj?.tly, detObj?.brx, detObj?.bry]}`}>
                            <canvas ref={canvasRef} style={{height: '100%'}}/>
                        </Tooltip>}
                </Box>
            </Box>
            <Box sx={{display: 'flex', width: '100%'}}>
                <Button sx={{width: '50%'}} variant='outlined'>Previous</Button>
                <Button sx={{width: '50%'}} variant='outlined'>Next</Button>
            </Box>
        </Box>
    )
}

export default ObjectPage
