import chai from "chai";
import chaiHttp from "chai-http";
import fs from "fs";
import path from "path";

chai.use(chaiHttp);
const expect = chai.expect;
const APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/europe-west1";

describe("test audible", () => {
    it(`test get_audible_version`, async () => {
        let countryCode = "ca"
        const response = await chai
            .request(APP_URL)
            .post("/get_audible_version")
            .send({ country_code: countryCode });

        expect(response).to.have.status(200);
        const result = response.body;
        expect(result).to.have.property("message");
        expect(result.message).to.equal("Audible version retrieved successfully");
        expect(result).to.have.property("status");
        expect(result.status).to.equal("success");
        expect(result).to.have.property("version");
        expect(result.version).to.be.a('string');

        console.log("Audible version:", result.version);
    });
    it(`test audible_download_file`, async () => {

        // Read the auth file
        const authFilePath = path.join(process.cwd(), 'audible_credentials.json');
        const authData = JSON.parse(fs.readFileSync(authFilePath, 'utf8'));
        const asin = "B08DJC7DQV"
        const response = await chai
            .request(APP_URL)
            .post("/audible_download_file")
            .send({ 
                country_code: "ca",
                auth: authData,
                asin: asin,
                bucket: "visibl-dev-ali",
                path: `UserData/uid/Uploads/RawAax/${asin}.aax`
            });

        expect(response).to.have.status(200);
        const result = response.body;
        expect(result).to.have.property("message");
        expect(result.message).to.equal("Audible file downloaded and uploaded successfully");
        expect(result).to.have.property("status");
        expect(result.status).to.equal("success");
        expect(result).to.have.property("output");
        expect(result.output).to.be.a('string');
        expect(result).to.have.property("storage_path");
        expect(result.storage_path).to.be.a('string');
        expect(result.storage_path).to.equal(`UserData/uid/Uploads/RawAax/${asin}.aax`);
        console.log("Storage path:", result.storage_path);
        console.log("Output:", result.output);
    });
    const DELETE_FILES = true;
    if(DELETE_FILES) {
    it('test delete downloaded files', async () => {
        const downloadsPath = path.join(process.cwd(), '..', 'functions', 'audible-cli', 'downloads');
        
        // Read the directory
        const files = fs.readdirSync(downloadsPath);
        
        // Delete each file
        for (const file of files) {
            fs.unlinkSync(path.join(downloadsPath, file));
        }
        
        // Check if the directory is empty
        const remainingFiles = fs.readdirSync(downloadsPath);
        expect(remainingFiles.length).to.equal(0);
        console.log(`Deleted ${files.length} files from ${downloadsPath}`);
        // Delete files in ../functions/audible-cli
        const audibleCliPath = path.join(process.cwd(), '..', 'functions', 'audible-cli');
        const audibleCliFiles = fs.readdirSync(audibleCliPath);
        
        for (const file of audibleCliFiles) {
            const filePath = path.join(audibleCliPath, file);
            if (fs.lstatSync(filePath).isFile()) {
                fs.unlinkSync(filePath);
            }
        }
        // Check if the directory is empty of files (might still contain subdirectories)
        const remainingAudibleCliFiles = fs.readdirSync(audibleCliPath).filter(file => 
            fs.lstatSync(path.join(audibleCliPath, file)).isFile()
        );
        expect(remainingAudibleCliFiles.length).to.equal(0);
        
        console.log(`Deleted ${audibleCliFiles.length} files from ${audibleCliPath}`);

        
        });
    }
});
    