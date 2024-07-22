import chai from "chai";
import chaiHttp from "chai-http";

chai.use(chaiHttp);
const expect = chai.expect;
const APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/us-central1";

describe("test audible", () => {
    it(`test get_login_url`, async () => {
        let countryCode = "ca"
        const response = await chai
            .request(APP_URL)
            .post("/get_login_url")
            .send({ country_code: countryCode });

        expect(response).to.have.status(200);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Login URL generated successfully");
        expect(result).to.have.property("login_url");
        expect(result).to.have.property("code_verifier");
        expect(result).to.have.property("serial");
        expect(result.login_url).to.be.a('string');
        expect(result.login_url).to.include('amazon.ca');
        console.log(`COUNTRY_CODE: ${countryCode}`);
        console.log(`CODE_VERIFIER: ${result.code_verifier}`);
        console.log(`SERIAL: ${result.serial}`);
        console.log(`LOGIN_URL: ${result.login_url}`);
    });
});
    