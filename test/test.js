import chai from "chai";
import chaiHttp from "chai-http";

chai.use(chaiHttp);
const expect = chai.expect;
const APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/us-central1";

describe("test audible", () => {
    it(`test on_request_example`, async () => {    
        const response = await chai
            .request(APP_URL)
            .post("/on_request_example")
            .send({});
    
        expect(response).to.have.status(200);
        const result = response.body;
    
        console.log(result);
        expect(result).to.have.property("message");
    });
    it(`test refresh_audible_tokens`, async () => {
        const fs = await import('fs');
        const path = await import('path');

        const credentialsPath = path.join(process.cwd(), 'audible_credentials.json');
        const auth = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));

        const response = await chai
            .request(APP_URL)
            .post("/refresh_audible_tokens")
            .set('Content-Type', 'application/json')
            .send(JSON.stringify({auth}));

        expect(response).to.have.status(200);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Audible tokens refreshed successfully");
        expect(result).to.have.property("updated_auth");
        expect(result.updated_auth).to.have.property("access_token");
        expect(result.updated_auth).to.have.property("refresh_token");
        expect(Number(result.updated_auth.expires)).to.be.greaterThan(Number(auth.expires));
        // Save the updated auth data to audible_credentials.json
        const updatedAuth = result.updated_auth;
        fs.writeFileSync(credentialsPath, JSON.stringify(updatedAuth, null, 2));
        console.log("Updated auth data saved to audible_credentials.json");

        // Verify that the file was updated
        const newAuth = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
        expect(newAuth).to.deep.equal(updatedAuth);
    });
});
    