import Box from '@mui/material/Box';
import {useLoaderData, useOutletContext, useParams} from "react-router-dom";
import {getRequest} from "../api/requests";
import {FC, useEffect, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setTitle} from "../reducers/appBarSlice";
import {setDoc} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {Button} from "@mui/material";
import {DetectedObject} from "../api/models/object";
import {Label} from "../api/models/label";


const AnnotationView: FC = () => {
    const {projectName, docId} = useParams();
    const context: any = useOutletContext();
    const idoc: any = useLoaderData();
    const imgContainer = useRef<HTMLDivElement>(null)

    const dispatch = useDispatch();
    // global state (redux)
    const showObjs: boolean = useSelector((state: any) => state.iDoc.showObjects);
    const labelsMap: Map<string, Label> | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);

    function onDownloadDocument(dataType: string, documentName: string) {
        // TODO: download annotation file and optionally the image (separately)
        // TODO: use the COCO annotation format (file contains doc id and file name to denote which image it refers to):
        //  https://towardsdatascience.com/image-data-labelling-and-annotation-everything-you-need-to-know-86ede6c684b1
        let fileData = ""
        const blob = new Blob([fileData], {type: "text/plain"});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.download = name + ".txt";
        link.href = url;
        link.click();
    }

    const loadProject = async () => {
        if (projectName) {
            const projectData = await getRequest('project/fromUser', encodeURIComponent(projectName!))
            if (projectData) {
                dispatch(setProject(projectData.result));
            }
        }
    }

    useEffect(() => {
        if (!project) {
            loadProject()
        }
    }, [projectName]);

    useEffect(() => {
        let document = idoc.doc
        if (document) {
            let objs: DetectedObject[] = document.objects;

            dispatch(setTitle(document.name));
            dispatch(setDoc(document))
        }
    }, [idoc.doc]);

    useEffect(() => {
        // context.setControlPanel(<DocControlPanel/>)
    }, []);

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
                    {idoc.src &&
                        <img alt={idoc.doc ? idoc.doc.name : "preview image"} src={idoc.src} style={{height: '100%'}}/>}
                </Box>
            </Box>
            <Box sx={{display: 'flex', width: '100%'}}>
                <Button sx={{width: '50%'}} variant='outlined'>Previous</Button>
                <Button sx={{width: '50%'}} variant='outlined'>Next</Button>
            </Box>
        </Box>
    )
}

export default AnnotationView
