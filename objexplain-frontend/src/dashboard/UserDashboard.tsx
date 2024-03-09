import {FC, useEffect, useState} from 'react';
import DeleteIcon from '@mui/icons-material/Delete';
import {
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Divider,
    IconButton,
    List,
    ListItem,
    ListItemIcon,
    Skeleton,
    TextField,
    Typography
} from "@mui/material";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import ListItemText from "@mui/material/ListItemText";
import ListItemButton from "@mui/material/ListItemButton";
import Avatar from "@mui/material/Avatar";
import {useDispatch, useSelector} from "react-redux";
import {deleteRequest, getRequest, postRequest} from "../api/requests";
import {login} from "../reducers/userSlice";
import {useNavigate} from "react-router-dom";
import CircularProgressWithLabel from "../components/ProgressCircleIcon";
import {ProjectStats} from "../api/models/project";
import {clearDoc, enableAnnoMode} from "../reducers/idocSlice";


const UserDashboard: FC = () => {
    // TODO: make another Lane (for Project Managers or Admins) with "My Projects"
    // TODO: Make a headline for each project lane ("My Projects" and "Shared/Assigned Projects")
    const [projectData, setProjectData] = useState<ProjectStats[] | undefined>();
    const [projectName, setProjectName] = useState('');
    const [openDelete, setOpenDelete] = useState<number>(-1);
    const [openCreate, setOpenCreate] = useState(false);
    const [error, setError] = useState(false);

    const dispatch = useDispatch()
    const navigate = useNavigate()

    // global state (redux)
    const userInfo = useSelector((state: any) => state.user.value);

    let isProjectSelected = !!projectData && 0 <= openDelete && openDelete < projectData.length

    const handleClickOpen = () => {
        setOpenCreate(true);
    };

    const handleDialogClose = () => {
        setProjectName('');
        setError(false);
        setOpenCreate(false);
    };

    const handleClickOpenDelete = (index: number) => {
        setOpenDelete(index);
    };

    const handleCloseDelete = () => {
        setOpenDelete(-1);
    };

    const handleChange = (event: any) => {
        setProjectName(event.target.value);
    }

    const openProject = (projectName: string) => {
        console.log("Opens project: " + projectName)
        navigate("/project/" + encodeURIComponent(projectName));
    }

    const handleCreateDialogClick = async (event: any) => {
        event.preventDefault();
        if (projectName === '' || projectName.trim() === '') {
            setError(true)
            return
        }
        console.log('handleClick 👉️', projectName)
        try {
            let result = await postRequest('project', {title: projectName})
            if (result) {
                openProject(projectName)
            }
            handleDialogClose()
        } catch (error) {
            handleDialogClose()
        }
    }

    const deleteProject = async () => {
        if (isProjectSelected) {
            let delId = projectData![openDelete]._id
            projectData!.splice(openDelete, 1)
            setProjectData(projectData!);
            let result = await deleteRequest('project', delId, undefined, true)
            console.log('Deleted Project with ID ' + delId)
            setOpenDelete(-1)
        }
    }

    const loadProjects = async () => {
        // load in the list of projects belonging to the current user and set the projectList
        let data = await getRequest('project/fromUser', undefined, {title: 1})
        if (data) {
            let result = data.result
            let projects: ProjectStats[] = []
            for (let i = 0; i < result.length; i++) {
                let reducedProject = result[i]
                projects.push(reducedProject)
            }
            projects.sort((a, b) => a.title > b.title ? 1 : b.title > a.title ? -1 : 0)
            // console.log(result)
            return projects
        }
    }

    const loadUser = async () => {
        // load in the list of projects belonging to the current user and set the projectList
        let data = await getRequest('user/current')
        if (data) {
            data = data.result
            console.log('Logged in as: ' + data.email)
            dispatch(login(data))
        }
    }

    const findLatestWork = async () => {
        // load in the list of projects belonging to the current user and set the projectList
        let data = await getRequest('workEntry/latest', undefined, {docId: 1, projectId: 1})
        if (data) {
            data = data.result;
            dispatch(clearDoc());
            dispatch(enableAnnoMode());
            navigate(`/project/${encodeURIComponent(data.projectTitle)}/idoc/${data.docId}`);
            return data
        }
    }

    useEffect(() => {
        if (projectData === undefined) {
            loadProjects().then(projects => setProjectData(projects))
        }
    }, [])

    const generateProjectList = () => {
        // TODO: also show project tags, if present
        return <List className="projects" key="mainList">{projectData?.map((proj, index) =>
            <ListItem divider key={'projItem' + index}>
                <ListItemButton key={'projButt' + index} sx={{py: 0}}
                                onClick={() => openProject(proj.title)}>
                    <ListItemIcon sx={{color: 'text.secondary'}} key={'projIcon' + index}>
                        {index + 1}
                    </ListItemIcon>
                    <ListItemText key={'projText' + index}>
                        <Box sx={{mt: 1}}>
                            <Typography variant='h6' color='primary.light'><b>{proj.title}</b></Typography>
                            <Typography variant="caption"
                                        sx={{ml: 2}}>Documents: {proj.numDocs}</Typography>
                        </Box>
                    </ListItemText>
                    <CircularProgressWithLabel value={proj.numDocs > 0 ? proj.progress : 0}/>
                </ListItemButton>
                <ListItemIcon>
                    <IconButton aria-label="comment" onClick={() => handleClickOpenDelete(index)}>
                        <DeleteIcon sx={{color: 'text.secondary'}}/>
                    </IconButton>
                </ListItemIcon>
            </ListItem>
        )}</List>
    }

    return (
        <Box sx={{display: 'flex'}}>
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    height: '92.9vh',
                    overflow: 'auto',
                }}
            >
                <Container maxWidth="xl" sx={{mt: 4, mb: 4, marginTop: "100pt"}}>
                    <Grid container spacing={3} rowSpacing={3}
                          sx={{marginLeft: "15%", width: "35%", float: "left"}}>
                        <Grid item xs={12} md={12} lg={12}>
                            <Paper elevation={6}
                                   sx={{
                                       px: 2, pb: 2, pt: 1,
                                       display: 'flex',
                                       flexDirection: 'column',
                                       height: 625,
                                       overflow: 'auto'
                                   }}>
                                <Paper elevation={0}
                                       sx={{
                                           px: 2, py: 0,
                                           display: 'flex',
                                           flexDirection: 'column',
                                           height: 585,
                                           overflow: 'auto'
                                       }}>
                                    {projectData !== undefined ? generateProjectList() : (<>
                                            <Skeleton variant="rectangular" sx={{mt: '20px'}} width='auto' height={20}/>
                                            <Skeleton variant="rectangular" sx={{mt: '10px'}} width={'auto'}
                                                      height={20}/>
                                            <Skeleton variant="rectangular" sx={{mt: '10px'}} width={'auto'}
                                                      height={20}/>
                                        </>
                                    )}
                                </Paper>
                                <Button variant={"contained"} style={{
                                    backgroundColor: "primary",
                                    margin: 1,
                                    textTransform: "none",
                                    width: "97%"
                                }} onClick={handleClickOpen} type="submit"> new project </Button>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} md={12} lg={12}>
                            <Dialog open={openCreate} onClose={handleDialogClose}>
                                <DialogTitle>New Project</DialogTitle>
                                <DialogContent>
                                    <DialogContentText>
                                        Please type in the name of the new project!
                                    </DialogContentText>
                                    <TextField
                                        error={error}
                                        onChange={handleChange}
                                        autoFocus
                                        margin="dense"
                                        id="name"
                                        label="Project Name"
                                        type="text"
                                        fullWidth
                                        required={true}
                                        variant="standard"
                                    />
                                </DialogContent>
                                <DialogActions>
                                    <Button onClick={handleCreateDialogClick}>Create</Button>
                                    <Button onClick={handleDialogClose}>Cancel</Button>
                                </DialogActions>
                            </Dialog>
                        </Grid>
                    </Grid>

                    <Grid container spacing={3} rowSpacing={3}
                          sx={{marginLeft: "10pt", width: "30%", float: "left"}}>
                        <Grid item xs={12} md={12} lg={12}>
                            <Paper
                                elevation={6}
                                sx={{
                                    p: 2,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    height: 625,
                                }}>
                                {userInfo !== undefined ?
                                    <Box sx={{mt: 3, mx: 2, width: '92%'}}>
                                        <Avatar sx={{
                                            bgcolor: userInfo ? userInfo.color : 'grey', ml: '42%',
                                            width: 50, height: 50, border: '1px solid #878787'
                                        }} alt={userInfo && userInfo.name ? userInfo.name : "User Icon"} src="todo"/>
                                        <br/>
                                        <Typography variant={"overline"}>Username:</Typography>
                                        <Typography variant={"h5"} color={"gray"}
                                                    align={'center'}>{userInfo?.name}</Typography>
                                        <br/>
                                        <Typography variant={"overline"}>Email:</Typography>
                                        <Typography variant={"h5"} color={"gray"} sx={{mb: 2}}
                                                    align={'center'}>{userInfo?.email}</Typography>
                                        <Divider/>
                                        <Button sx={{mt: 2, width: '100%', height: '15%', fontSize: 16}}
                                                onClick={findLatestWork}>
                                            Continue your Work
                                        </Button>
                                    </Box> :
                                    <>
                                        <Skeleton variant="rectangular" width={'auto'} height={20}/>
                                        <Skeleton variant="rectangular" style={{marginTop: '10px'}}
                                                  width={'auto'} height={20}/>
                                        <Skeleton variant="rectangular" style={{marginTop: '10px'}} width={'auto'}
                                                  height={20}/>
                                    </>}
                            </Paper>
                        </Grid>

                        <Dialog open={isProjectSelected}
                                onClose={handleCloseDelete}>
                            <DialogTitle sx={{color: 'red'}}>Delete
                                Project: {isProjectSelected ? projectData![openDelete].title : ''}?</DialogTitle>
                            <DialogContent>
                                <DialogContentText>
                                    Do you really want to delete this project?
                                </DialogContentText>
                            </DialogContent>
                            <DialogActions>
                                <Button variant="contained" color="error" sx={{marginRight: '50%'}}
                                        onClick={deleteProject}>delete</Button>
                                <Button onClick={handleCloseDelete}>Cancel</Button>
                            </DialogActions>
                        </Dialog>
                    </Grid>

                </Container>
            </Box>
        </Box>
    )
}

export default UserDashboard;
