import chai from "chai";
import chaiHttp from "chai-http";
import dotenv from "dotenv";
let ENV_PATH = `${process.cwd()}/../functions/.env.local`;

dotenv.config({ path: ENV_PATH });
chai.use(chaiHttp);
const expect = chai.expect;
const APP_URL = process.env.APP_URL;
const API_KEY = process.env.API_KEY;
const COUNTRY_CODE = process.env.COUNTRY_CODE || "uk";
describe("test audible", () => {
    it(`test get_login_url with wrong API key`, async () => {
        const response = await chai
            .request(APP_URL)
            .post("/get_login_url")
            .set("API-KEY", "WRONG_API_KEY")
            .send({ country_code: COUNTRY_CODE });

        expect(response).to.have.status(401);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Invalid API key");
        expect(result).to.have.property("status");
        expect(result.status).to.equal("error");
    });
    it(`test get_login_url`, async () => {
        const response = await chai
            .request(APP_URL)
            .post("/get_login_url")
            .set("API-KEY", API_KEY)
            .send({ country_code: COUNTRY_CODE });

        expect(response).to.have.status(200);
        const result = response.body;

        expect(result).to.have.property("message");
        expect(result.message).to.equal("Login URL generated successfully");
        expect(result).to.have.property("login_url");
        expect(result).to.have.property("code_verifier");
        expect(result).to.have.property("serial");
        expect(result.login_url).to.be.a('string');
        expect(result.login_url).to.include('amazon');
        console.log(`COUNTRY_CODE: ${COUNTRY_CODE}`);
        console.log(`CODE_VERIFIER: ${result.code_verifier}`);
        console.log(`SERIAL: ${result.serial}`);
        console.log(`LOGIN_URL: ${result.login_url}`);
    });
});
    