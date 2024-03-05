import React from 'react';
import axios from 'axios';
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@mui/material";
import "./Documents.css"
import {useParams} from "react-router-dom";
import ButtonTextfield from "../components/ButtonTextfield";


interface DocumentsProps {
    onDownloadDocument: Function
    currDocInfo: string[]
    documentsInfo: [string, string][] | undefined
    setDocumentsInfo: Function
    renameDocument: Function
    unsavedChanges: boolean
    saveChanges: Function
    clearChanges: Function
}

// Close the dropdown if the user clicks outside of it
window.onclick = function (event) {
    // @ts-ignore
    if (!event.target!.matches('.dropbtn')) {
        let dropdowns = document.getElementsByClassName("dropdown-content");
        for (let i = 0; i < dropdowns.length; i++) {
            let openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}


const Documents: React.FC<DocumentsProps> = ({
                                                 onDownloadDocument,
                                                 currDocInfo,
                                                 setDocumentsInfo,
                                                 documentsInfo,
                                                 renameDocument,
                                                 saveChanges,
                                                 clearChanges,
                                                 unsavedChanges
                                             }) => {

    const {projectname} = useParams();
    const [selectedFile, setSelectedFile] = React.useState<any | null>(null);
    const supportedDataTypes = ["XML", "CoNLL-2012", "plaintext"];
    const [saveOpen, setSaveOpen] = React.useState(false);


    // On file download (click the download button)
    const onFileDownload = (event: any) => {
        document.getElementById("documentsDropDown")!.classList.toggle("show");
    };

    function openSaveDialog() {
        setSaveOpen(true);
    }

    function closeSaveDialog() {
        setSaveOpen(false);
    }

    // On file select (from the pop up)
    const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        // Update the state
        let y = (event?.target as HTMLInputElement).files;
        let file = null;
        if (y != null) {
            file = y[0];
        }
        setSelectedFile(file);
    };

    // On file upload (click the upload button)
    const onFileUpload = async (event: any) => {
        if (selectedFile !== null && documentsInfo !== undefined) {
            let fileName = selectedFile.name
            let formData = new FormData();
            formData.append('myFile', selectedFile);
            formData.append('docname', fileName);
            formData.append('projectname', projectname!);

            try {
                const {data} = await axios.post(
                    `http://127.0.0.1:5000/uploadfile`,
                    formData,
                    {
                        withCredentials: true,
                        headers: {
                            'Access-Control-Allow-Origin': '*',
                            'Content-Type': 'multipart/form-data',
                        },
                    },
                );
                if (data.status === 201) {
                    let result = data.result
                    window.history.replaceState(null, "Coref-App", "/idoc/" + result.name)
                    // TODO: trigger pop-up if changes in current doc should be changed
                }  // TODO: handle unauthorized and other errors (make button not clickable when not logged in?)
            } catch (error) {
                if (axios.isAxiosError(error)) {
                    console.log('error message: ', error.message);
                    return error.message;
                } else {
                    console.log('unexpected error: ', error);
                    return 'An unexpected error occurred';
                }
            }
            setSelectedFile(null);
        }
        if (document !== null && document.getElementById('file') !== null) {
            (document.getElementById('file') as HTMLInputElement).value = '';
        }
    };

    return (
        <div>
            <input type="file" id="file" onChange={onFileChange} accept=".txt"/>
            <Button variant="outlined" style={{margin: 1, textTransform: "none", width: "97%"}}
                    onClick={unsavedChanges ? openSaveDialog : onFileUpload} type="submit"
                    disabled={!selectedFile}> Upload </Button>
            <ButtonTextfield tfLabel="New Document Name" buttonText="Rename" submitFunc={renameDocument} clearOnSubmit/>
            <span className="dropdown">
                <Button disabled={currDocInfo.length === 0} variant="outlined"
                        style={{margin: 5, textTransform: "none", width: "97%"}}
                        onClick={onFileDownload} className="dropbtn">
                    Download annotated document</Button>
                <div id="documentsDropDown" className="dropdown-content">
                    {supportedDataTypes.map((dataTypes, index) =>
                        (<a key={"DT-" + index + 1} onClick={() => onDownloadDocument(dataTypes, "TestName")}>
                            {supportedDataTypes[index]}</a>))}
                </div>
            </span>
            <Button variant="outlined" style={{margin: 5, textTransform: "none", width: "97%"}} disabled>
                Share selected document</Button>
            <Button variant="outlined" style={{margin: 5, textTransform: "none", width: "97%"}} disabled>
                Submit annotation <br/>(Submit for online learning)</Button>

            <Dialog open={saveOpen} onClose={() => closeSaveDialog()}>
                <DialogTitle sx={{color: 'red'}}>Unsaved changes!</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Please save or discard your changes before you upload another document.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="outlined" sx={{marginRight: '70%'}} onClick={() => {
                        saveChanges();
                        closeSaveDialog()
                    }}>save</Button>
                    <Button variant="outlined" color="error" onClick={() => {
                        clearChanges();
                        closeSaveDialog()
                    }}>discard</Button>
                </DialogActions>
            </Dialog>
        </div>
    );
}

export default Documents;
