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
import {setObjectIdx} from "../reducers/objectSlice";
import {setDoc, setLabelMap} from "../reducers/idocSlice";
import {mapLabels} from "../document/DocControl";


export const FEATURE_COLORS = [
    '#9A6324',
    '#808000',
    '#469990',
    '#FFD8B1',
    '#DCBEFF',
    '#404040',
    '#AAFFC3',
    '#F032E6',
    '#6495ED',
    '#228B22',
]

const ObjectPage: FC = () => {
    const {projectName, docId, objIdx} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null)

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: Map<string, Label> | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);

    const cropImage = (imagePath: string, newX: number, newY: number, newWidth: number, newHeight: number) => {
        //create an image object from the path
        const originalImage = new Image();
        originalImage.src = imagePath;

        //initialize the canvas object
        const canvas: any = document.getElementById('canvas');
        const ctx = canvas?.getContext('2d');

        //wait for the image to finish loading
        originalImage.addEventListener('load', function () {

            //set the canvas size to the new width and height
            canvas.width = newWidth;
            canvas.height = newHeight;

            //draw the image
            ctx.drawImage(originalImage, newX, newY, newWidth, newHeight, 0, 0, newWidth, newHeight);
        });
    }

    const loadProject = async () => {
        if (projectName) {
            return await getRequest('project/fromUser', encodeURIComponent(projectName!))
        } else {
            navigate('/notfound404')
        }
    }

    const loadDoc = async () => {
        if (docId) {
            return await getRequest('idoc', docId)
        }
        navigate('/notfound404')
    }

    useEffect(() => {
        if (!project) {
            loadProject().then(projectData => projectData && dispatch(setProject(projectData.result)))
        }
        let document = idoc;
        if (document) {
            dispatch(setTitle(document.name));
        } else {
            loadDoc().then(idocData => {
                if (idocData) {
                    dispatch(setDoc(idocData.result));
                    dispatch(setTitle(idocData.result.name));
                }
            })
        }
        context.setControlPanel(<ObjectControlPanel/>)
    }, []);

    useEffect(() => {
        if (!labelsMap) {
            mapLabels(idoc).then(lm => lm && dispatch(setLabelMap(lm)));
        }
        if (objIdx) {
            let idx = parseInt(objIdx);
            if (idoc && idoc.objects) {
                if (idx >= 0 && idx < idoc.objects.length) {
                    dispatch(setObjectIdx(idx));
                } else {
                    navigate('/notfound404')
                }
            }
        } else {
            navigate('/notfound404')
        }
    }, [idoc]);

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
