import {FC, useState} from "react";
import Box from "@mui/material/Box";
import {Button, ButtonGroup, Divider, FormControlLabel, FormGroup, IconButton, Switch} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {clearBbox, toggleMovable, toggleShowObjs} from "../reducers/objectCreateSlice";
import LabelSelect from "./LabelSelector";
import {clearObject} from "../reducers/objectSlice";
import {clearDoc, disableAnnoMode} from "../reducers/idocSlice";


interface NewObjectControlProps {
    resetZoomCallback: Function;
}

const NewObjectControlPanel: FC<NewObjectControlProps> = ({resetZoomCallback}) => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const isMoveImg: boolean = useSelector((state: any) => state.newObj.isMoveImg);
    const showObjs: boolean = useSelector((state: any) => state.newObj.showCurrObjs);

    const toProjectView = () => {
        if (project) {
            dispatch(clearObject())
            dispatch(clearBbox())
            dispatch(clearDoc())
            dispatch(disableAnnoMode())
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toImageView = () => {
        if (project && idoc) {
            dispatch(clearObject())
            dispatch(clearBbox())
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}`)
        }
    }

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toImageView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>Create new
                Object {idoc && idoc.objects && idoc.objects.length + 1}</Typography>
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch defaultChecked={showObjs}
                                                   onChange={() => dispatch(toggleShowObjs())}/>}
                                  label="Show Objects" sx={{mr: 6}}/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 0.5, color: 'primary'}} variant='subtitle1'>Instructions:</Typography>
            <Typography sx={{mb: 0.2, color: 'primary.light'}} variant='subtitle2'>Drag over the image with your cursor
                to create a Bounding Box of an object.</Typography>
            <Typography sx={{mb: 0.2, color: 'primary.light'}} variant='subtitle2'>Write or select a label that best
                describes the object in your bounding box.</Typography>
            <Typography sx={{mb: 0.2, color: 'primary.light'}} variant='subtitle2'>If you create a new class label, you
                must add at least one category for the label, in which the object falls into (e.g. bird, car, ship
                etc.).</Typography>
            <Typography sx={{mb: 0.2, color: 'primary.light'}} variant='subtitle2'>Click "Insert Object" to add the
                object to the image.</Typography>
            <Divider sx={{my: 1}}/>
            <LabelSelect labelCaption="Select Object Label and Categories" labelButtonText='Insert Object'
                         categoriesDescriptor='Choose for Categories for this Object Label: ' categoryButtonText='Add'
                         projectName={project?.title} makeNewObject
                         categoriesCaption='Currently assigned Label Categories (min. 1 category required):'
                         setAlertContent={setAlertContent} setAlertSeverity={setAlertSeverity}/>
            <Divider sx={{my: 1}}/>
            <ButtonGroup sx={{width: '100%', bottom: 5}}>
                <Button onClick={() => dispatch(toggleMovable())} variant={isMoveImg ? "outlined" : "contained"}
                        sx={{flexGrow: 50}}>
                    Move / Zoom in Image
                </Button>
                <Button onClick={() => resetZoomCallback()} variant="outlined" sx={{ml: 2, flexGrow: 50}}>
                    Reset Image Position
                </Button>
            </ButtonGroup>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default NewObjectControlPanel
