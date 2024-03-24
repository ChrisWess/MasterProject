import {FC, SyntheticEvent, useEffect, useState} from "react";
import Box from "@mui/material/Box";
import {Divider, IconButton, Tab, Tabs} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {DetectedObject} from "../api/models/object";
import {clearObject} from "../reducers/objectSlice";
import {clearDoc, disableAnnoMode} from "../reducers/idocSlice";
import {clearNewAnnoView, setMode} from "../reducers/annotationCreateSlice";
import TabPanel from "../components/TabPanel";
import {Annotation} from "../api/models/annotation";
import ConceptsController from "./ConceptsController";
import AnnoWriteController from "./AnnoWriteController";


const NewAnnotationControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const modeId: number = useSelector((state: any) => state.newAnno.modeId);
    const annotation: Annotation | undefined = useSelector((state: any) => state.newAnno.newAnnotation);

    const toProjectView = () => {
        if (project) {
            dispatch(clearNewAnnoView())
            dispatch(clearObject())
            dispatch(clearDoc())
            dispatch(disableAnnoMode())
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toObjectView = () => {
        if (project && idoc && objIdx !== undefined) {
            dispatch(clearNewAnnoView())
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}`)
        }
    }

    const handleChange = (event: SyntheticEvent, newValue: number) => {
        dispatch(setMode(newValue));
    };

    useEffect(() => {

    }, []);

    let newAnnoIdx = detObj?.annotations ? detObj.annotations.length : -1

    // TODO: allow saving how often an annotation has been selected in "Text Writer".
    //  Present annotations that are selected often for a type of object more often to users.
    //  Append selected annotation to the text areas' current text.
    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toObjectView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}}
                        variant='h5'>Create New Annotation {newAnnoIdx + 1}</Typography>
            <Divider sx={{my: 1}}/>
            <Box sx={{width: '100%'}}>
                <Box sx={{borderBottom: 1, borderColor: 'divider'}}>
                    <Tabs value={modeId} onChange={handleChange} aria-label="annotation type tabs">
                        <Tab label="Text Writer"/>
                        <Tab label="Concept Selector"/>
                        <Tab disabled={!annotation} label="Inspect new Annotation"/>
                    </Tabs>
                </Box>
                <TabPanel value={modeId} index={0}>
                    <AnnoWriteController/>
                </TabPanel>
                <TabPanel value={modeId} index={1}>
                    <ConceptsController/>
                </TabPanel>
                <TabPanel value={modeId} index={2}>
                    <>
                        <Typography variant='h5'>Inspect and verify your new annotation</Typography>
                        <Typography variant='subtitle1'>Show list of concepts here and show the highlighted annotation
                            in the lower right panel.</Typography>
                    </>
                </TabPanel>
            </Box>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default NewAnnotationControlPanel
