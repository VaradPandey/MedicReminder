import mongoose from "mongoose";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.ACCESS_TOKEN_SECRET || "dev-secret";
const JWT_EXPIRY = process.env.ACCESS_TOKEN_EXPIRY || "1h";

const userSchema=new mongoose.Schema({
    username:{
        type: String,
        required: true,
        lowercase: true,
        unique: true,
    },
    email:{
        type: String,
        required: true,
    },
    phone:{
        type: String,
        required: true,
    },
    password:{
        type: String,
        required: true,
    },
    avatar:{
        type:String,
        default: ""
    },
},{timestamps: true});

userSchema.pre('save',async function(next){
    if(!this.isModified("password")){
        next();
        return;
    }

    this.password=await bcrypt.hash(this.password,10);
    next();
});

userSchema.methods.isPasswordCorrect=async function(password){
    return await bcrypt.compare(password,this.password);
}

userSchema.methods.setUser=async function(){
    const payload={
        _id: this._id,
        username: this.username,
        email: this.email
    }

    return jwt.sign(payload,JWT_SECRET,{expiresIn: JWT_EXPIRY});
}

export const User=mongoose.model('User',userSchema);