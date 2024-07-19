import chai from "chai";
import chaiHttp from "chai-http";

chai.use(chaiHttp);
const expect = chai.expect;
const APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/us-central1";

describe("test audible", () => {
    it(`test get_login_url for Canada`, async () => {
        const response = await chai
            .request(APP_URL)
            .post("/get_login_url")
            .send({ locale: 'ca' });

        expect(response).to.have.status(200);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Login URL generated successfully");
        expect(result).to.have.property("login_url");
        expect(result.login_url).to.be.a('string');
        expect(result.login_url).to.include('audible.ca');

        console.log("Login URL for Canada:", result.login_url);
    });
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
    it(`test get_activation_bytes`, async () => {
        const fs = await import('fs');
        const path = await import('path');

        const credentialsPath = path.join(process.cwd(), 'audible_credentials.json');
        const auth = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));

        const response = await chai
            .request(APP_URL)
            .post("/get_activation_bytes")
            .set('Content-Type', 'application/json')
            .send(JSON.stringify({auth}));

        expect(response).to.have.status(200);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Activation bytes retrieved successfully");
        expect(result).to.have.property("activation_bytes");
        expect(result.activation_bytes).to.be.a('string');
        expect(result.activation_bytes).to.have.lengthOf(8);

        console.log("Activation bytes:", result.activation_bytes);
    });

});
    