import {FC, useEffect, useState} from "react";
import Box from "@mui/material/Box";
import {Divider, IconButton} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {DetectedObject} from "../api/models/object";


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

    const toProjectView = () => {
        if (project) {
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toObjectView = () => {
        if (project && idoc && objIdx !== undefined) {
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}`)
        }
    }

    useEffect(() => {

    }, []);

    let newAnnoIdx = detObj?.annotations ? detObj.annotations.length : -1

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
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default NewAnnotationControlPanel
