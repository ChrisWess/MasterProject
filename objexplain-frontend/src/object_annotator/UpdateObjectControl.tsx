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
import {clearUpdObjectView, toggleMovable, toggleShowObjs} from "../reducers/objectCreateSlice";
import {clearDoc, disableAnnoMode, setDoc} from "../reducers/idocSlice";
import {clearObject, setObject} from "../reducers/objectSlice";
import {BoundingBoxCoords} from "../api/models/feature";
import {putRequest} from "../api/requests";


interface UpdObjectControlProps {
    resetZoomCallback: Function;
}

const UpdObjectControlPanel: FC<UpdObjectControlProps> = ({resetZoomCallback}) => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const currBbox: BoundingBoxCoords | undefined = useSelector((state: any) => state.newObj.newBbox);
    const isMoveImg: boolean = useSelector((state: any) => state.newObj.isMoveImg);
    const showObjs: boolean = useSelector((state: any) => state.newObj.showCurrObjs);

    const toProjectView = () => {
        if (project) {
            dispatch(clearUpdObjectView())
            dispatch(clearObject())
            dispatch(clearDoc())
            dispatch(disableAnnoMode())
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toObjectView = () => {
        if (project && idoc && objIdx !== undefined) {
            dispatch(clearUpdObjectView())
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}`)
        }
    }

    const submitBBoxUpdate = () => {
        if (objIdx !== undefined && idoc?.objects && currBbox) {
            let obj = idoc.objects[objIdx]
            let bbox = [currBbox.tlx, currBbox.tly, currBbox.brx, currBbox.bry]
            putRequest('object', {objectId: obj._id, bbox: bbox}).then(data => {
                if (data && idoc?.objects) {
                    let updObj = {...obj, ...currBbox}
                    dispatch(setObject(updObj))
                    let newObjs = idoc.objects
                    newObjs = [...newObjs.slice(0, objIdx), updObj, ...newObjs.slice(objIdx + 1)]
                    let updDoc = {...idoc, objects: newObjs}
                    dispatch(setDoc(updDoc))
                    setAlertContent('Updated Object Bounding Box!')
                    toObjectView()
                }
            })
        }
    }

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toObjectView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>
                Select new Bounding Box for Object {objIdx !== undefined && objIdx + 1}</Typography>
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch checked={showObjs} onChange={() => dispatch(toggleShowObjs())}/>}
                                  label="Show Other Objects" sx={{mr: 6}}/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <Button variant="contained" sx={{width: '100%', textTransform: 'none', mb: 2}}
                    disabled={!currBbox} onClick={submitBBoxUpdate}>
                Update Bounding Box to current Selection
            </Button>
            <ButtonGroup sx={{width: '100%', bottom: 5}}>
                <Button onClick={() => dispatch(toggleMovable())} variant={isMoveImg ? "contained" : "outlined"}
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

export default UpdObjectControlPanel
