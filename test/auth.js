import chai from "chai";
import chaiHttp from "chai-http";
import fs from 'fs';
import path from 'path';

chai.use(chaiHttp);
const expect = chai.expect;
const APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/europe-west1";

describe("test audible", () => {
    let auth;
    it(`test do_login`, async () => {
        let countryCode = process.env.COUNTRY_CODE
        let code_verifier = process.env.CODE_VERIFIER
        const urlPath = path.join(process.cwd(), 'response_url.txt');
        let response_url = fs.readFileSync(urlPath, 'utf8').trim();
        let serial = process.env.SERIAL

        console.log(`COUNTRY_CODE: ${countryCode}`);
        console.log(`CODE_VERIFIER: ${code_verifier}`);
        console.log(`RESPONSE_URL: ${response_url}`);
        console.log(`SERIAL: ${serial}`);

        const response = await chai
            .request(APP_URL)
            .post("/do_login")
            .set("API-KEY", "LOCAL_API_KEY")
            .send({
                code_verifier: code_verifier,
                response_url: response_url,
                serial: serial,
                country_code: countryCode
            });

        expect(response).to.have.status(200);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Login process completed successfully");
        expect(result).to.have.property("status");
        expect(result.status).to.equal("success");
        expect(result).to.have.property("auth");
        expect(result.auth).to.be.an('object');
        // Check for activation_bytes in the response
        expect(result.auth).to.have.property("activation_bytes");
        expect(result.auth.activation_bytes).to.be.a('string');
        expect(result.auth.activation_bytes).to.have.lengthOf(8);

        console.log("Activation bytes:", result.auth.activation_bytes);
        
        // Check for essential properties in the login_url object
        expect(result.auth).to.have.property("access_token");
        expect(result.auth).to.have.property("refresh_token");
        expect(result.auth).to.have.property("expires");
        auth = result.auth;
    });
    it(`test refresh_audible_tokens`, async () => {
        const response = await chai
            .request(APP_URL)
            .post("/refresh_audible_tokens")
            .set('Content-Type', 'application/json')
            .set("API-KEY", "LOCAL_API_KEY")
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
        auth = updatedAuth;
        fs.writeFileSync('audible_credentials.json', JSON.stringify(auth, null, 2));
    });
    it(`test get_activation_bytes`, async () => {
        const response = await chai
            .request(APP_URL)
            .post("/get_activation_bytes")
            .set('Content-Type', 'application/json')
            .set("API-KEY", "LOCAL_API_KEY")
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
    