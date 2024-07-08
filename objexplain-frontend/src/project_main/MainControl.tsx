import {ChangeEvent, FC, useState} from "react";
import Box from "@mui/material/Box";
import {Button, Checkbox, Divider, FormControlLabel, FormGroup, LinearProgress, TextField} from "@mui/material";
import ButtonTextfield from "../components/ButtonTextfield";
import {useDispatch, useSelector} from "react-redux";
import {clearFilter, setFilter, setMaxPage, setProject} from "../reducers/mainPageSlice";
import {getRequest, postRequest, putRequest} from "../api/requests";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {Label} from "@mui/icons-material";
import {setTitle} from "../reducers/appBarSlice";
import {useNavigate} from "react-router-dom";
import {enableAnnoMode, loadInNewDocs} from "../reducers/idocSlice";
import {ImageDocument} from "../api/models/imgdoc";


const MainControlPanel: FC = () => {
    const [imageName, setImageName] = useState<string>('');
    const [imageFile, setImageFile] = useState<any>();
    const [importFile, setImportFile] = useState<any>();
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const isWorking: boolean = useSelector((state: any) => state.iDoc.annoMode);
    const cacheIdx: number = useSelector((state: any) => state.iDoc.fetchedIdx);
    const cachedDocs: ImageDocument[] | undefined = useSelector((state: any) => state.iDoc.fetchedDocs);
    const filter: string | undefined = useSelector((state: any) => state.mainPage.projectFilter);
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);

    const setSearchFilter = (textInput: string) => {
        dispatch(setFilter(textInput))
        dispatch(setMaxPage(undefined))
    }

    const onImageFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        let y = (event?.target as HTMLInputElement).files;
        if (y != null) {
            setImageFile(y[0])
        }
    };

    const insertImage = async (event: any) => {
        event.preventDefault();
        if (project && imageName.length >= 3 && !!imageFile) {
            let formData = new FormData();
            // TODO: allow upload of multi-selection of images directly from the file system
            //   => apply name to all these images with a suffix appended that marks the index e.g. (1), (2)...
            //   This spares us a manual zipping of all the image files, which makes this more convenient.
            formData.append('name', imageName);
            formData.append('image', imageFile);
            formData.append('projectId', project._id)

            let data = await postRequest('idoc', formData,
                'multipart/form-data image/jpeg image/png image/gif image/webp')
            if (data) {
                let result = data.result
                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${result}`)
            }
        }
    }

    const onImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        let y = (event?.target as HTMLInputElement).files;
        if (y != null) {
            setImportFile(y[0])
        }
    };

    const onSubmitDataset = async (event: any) => {
        // Uploads an export file or a dataset file.
        event.preventDefault();
        if (!importFile) {
            alert("Please select a file to upload!");
            return;
        }

        if (project) {
            let formData = new FormData();
            formData.append('file', importFile);
            // TODO: possibility to add categories
            const data = await putRequest('dataset/import', formData, project._id, 'multipart/form-data', {categories: 'bird'})
            if (data) {
                let result = data.numInserted
                if (result) {
                    dispatch(setMaxPage(undefined))
                    setAlertSeverity('success')
                    setAlertContent(result.toString() + ' Images were successfully uploaded to your project!')
                    const updatedData = await getRequest('project/fromUser', encodeURIComponent(project.title))
                    if (updatedData)
                        dispatch(setProject(updatedData.result))
                } else {
                    setAlertSeverity('info')
                    setAlertContent('The Dataset was empty. No Images were uploaded to your project!')
                }
            }
            setImportFile(undefined);
        }
    };

    const prepareWork = async () => {
        if (project) {
            if (cachedDocs) {
                let curr = cachedDocs[cacheIdx];
                dispatch(setTitle(curr.name));
                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${curr}`)
            } else {
                const data = await getRequest(`project/${project._id}/randfetch/5`)
                if (data) {
                    let result: ImageDocument[] = data.result;
                    let firstDoc = result[0]
                    dispatch(setTitle(firstDoc.name));
                    dispatch(loadInNewDocs(result));
                    navigate(`/project/${encodeURIComponent(project.title)}/idoc/${firstDoc._id}`)
                }
            }
        }
    }

    const renameProject = async (textInput: string) => {
        if (project) {
            let payload = {'projectId': project._id, 'title': textInput};
            const data = await putRequest('project/title', payload, undefined)
            if (data) {
                dispatch(setTitle(textInput))
                window.history.replaceState(null, "", "/project/" + encodeURIComponent(textInput))
            }
        }
    }

    const addMember = async (textInput: string) => {
        if (project) {
            let payload = {'projectId': project._id, 'userEmail': textInput};
            const data = await putRequest('project/member', payload, undefined)
            if (data) {
                setAlertSeverity('success')
                setAlertContent(textInput + ' was added as new member to the Project!')
            } else {
                setAlertSeverity('error')
                setAlertContent('User with E-Mail ' + textInput + ' was not found!')
            }
        }
    }

    const startWork = async () => {
        if (!isWorking) {
            dispatch(enableAnnoMode());
        }
        await prepareWork();
    }

    let progressVal = project?.progress ? Math.round(100 * project?.progress) : 0

    // TODO: show a small preview of the image after selecting it at the single image upload
    // TODO: stylizing file uploads: https://frontendshape.com/post/how-to-use-file-upload-in-react-mui-5
    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>Your Project Role: Maintainer</Typography>
            <Box sx={{display: 'flex', pb: 0.5}}>
                <LinearProgress variant="determinate" value={progressVal} color='secondary'
                                sx={{width: '92%', mt: '6px', mr: '3px'}}/>
                <Typography sx={{fontSize: '12px'}}>{progressVal}% </Typography>
            </Box>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 1, pt: 1}}>Search in Project
                Images{filter && ` (Current Filter: "${filter}")`}</Typography>
            <Box sx={{display: 'flex', pb: 1}}>
                <ButtonTextfield buttonText='' tfLabel='search' submitFunc={setSearchFilter} clearOnSubmit={false}
                                 icon='search'/>
                <Button sx={{textTransform: "none", width: '15%'}}
                        onClick={() => dispatch(clearFilter())}>Clear</Button>
            </Box>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 0.5, pt: 1}}>Image Upload</Typography>
            <Box sx={{display: 'flex', pb: 1}} component='form' onSubmit={insertImage}>
                <TextField size='small'
                           label='Image title'
                           onChange={(e) => {
                               e.preventDefault();
                               setImageName(e.target.value);
                           }}
                           value={imageName}
                           sx={{
                               mr: 1,
                               "& .MuiOutlinedInput-notchedOutline": {
                                   borderColor: "#9090C0",
                               },
                           }}/>
                <input style={{margin: 'auto'}} type="file" id="img-upload" onChange={onImageFileChange}
                       accept="image/jpeg,image/png,image/gif,image/webp"/>
                <Button variant="outlined"
                        sx={{textTransform: "none", flexGrow: 100}}
                        type="submit" disabled={!imageFile || imageName.trim().length < 3}>Upload</Button>
            </Box>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 0.5, pt: 1}}>Dataset Import</Typography>
            <Box sx={{display: 'flex'}} component='form' onSubmit={onSubmitDataset}>
                <input style={{margin: 'auto'}} type="file" id="data-import" onChange={onImportFileChange}
                       accept="application/zip,application/json"/>
                <Button variant="outlined"
                        sx={{m: 1, textTransform: "none", flexGrow: 100}}
                        type="submit" disabled={!importFile}>Import</Button>
            </Box>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 1, pt: 1}}>Rename Project</Typography>
            <ButtonTextfield buttonText='Rename' tfLabel='New name' submitFunc={renameProject} clearOnSubmit
                             style={{paddingBottom: 10}}/>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 1, pt: 1}}>Descriptional Project Tags</Typography>
            <Label>Tag 1</Label>
            <Divider sx={{my: 1}}/>
            <Typography sx={{pt: 1}}>Add Member to the Project</Typography>
            <FormGroup sx={{pb: 1}}>
                <FormControlLabel control={<Checkbox/>} label="Maintainer"/>
                <ButtonTextfield buttonText='Add User' tfLabel='E-Mail' submitFunc={addMember} clearOnSubmit/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <Box sx={{display: 'flex'}}>
                <Button variant="outlined" onClick={startWork} sx={{
                    backgroundColor: "primary",
                    fontSize: 18,
                    mt: 0.8, mx: 0.5,
                    textTransform: "none",
                    width: "97%"
                }}><b>Start Annotating high-priority Images</b></Button>
            </Box>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default MainControlPanel
