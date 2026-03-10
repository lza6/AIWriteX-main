/**
 * WebGPU 类型定义 (TypeScript)
 * 
 * 由于 WebGPU 仍处于标准化阶段，这里提供简化的类型定义
 */

// WebGPU 常量枚举
interface GPUBufferUsageFlags {
    MAP_READ: number;
    MAP_WRITE: number;
    COPY_SRC: number;
    COPY_DST: number;
    INDEX: number;
    VERTEX: number;
    UNIFORM: number;
    STORAGE: number;
    INDIRECT: number;
    QUERY_RESOLVE: number;
}

interface GPUTextureUsageFlags {
    COPY_SRC: number;
    COPY_DST: number;
    TEXTURE_BINDING: number;
    SAMPLED: number;
    STORAGE_BINDING: number;
    STORAGE: number;
    RENDER_ATTACHMENT: number;
}

// @ts-ignore - WebGPU 全局类型
const GPUBufferUsage: GPUBufferUsageFlags;
const GPUTextureUsage: GPUTextureUsageFlags;
interface Navigator {
    gpu?: GPU;
}

interface GPU {
    requestAdapter(options?: GPURequestAdapterOptions): Promise<GPUAdapter | null>;
    getPreferredCanvasFormat(): GPUTextureFormat;
}

interface GPURequestAdapterOptions {
    powerPreference?: 'low-power' | 'high-performance';
}

interface GPUAdapter {
    requestDevice(descriptor?: GPUDeviceDescriptor): Promise<GPUDevice>;
}

interface GPUDeviceDescriptor {
    requiredFeatures?: string[];
}

interface GPUDevice {
    createBuffer(descriptor: GPUBufferDescriptor): GPUBuffer;
    createShaderModule(descriptor: GPUShaderModuleDescriptor): GPUShaderModule;
    createRenderPipeline(descriptor: GPURenderPipelineDescriptor): GPURenderPipeline;
    createBindGroup(descriptor: GPUBindGroupDescriptor): GPUBindGroup;
    createCommandEncoder(): GPUCommandEncoder;
    queue: GPUQueue;
    destroy(): void;
}

interface GPUBufferDescriptor {
    size: number;
    usage: number;
    mappedAtCreation?: boolean;
}

interface GPUBuffer {
    size: number;
    getMappedRange(): ArrayBuffer;
    unmap(): void;
    destroy(): void;
}

// GPUShaderModule - GPU 着色器模块
interface GPUShaderModule {
    label?: string;
    getCompilationInfo(): Promise<any>;
}

interface GPUShaderModuleDescriptor {
    code: string;
    label?: string;
}

interface GPURenderPipelineDescriptor {
    layout: 'auto' | GPUPipelineLayout;
    vertex: GPUVertexState;
    fragment?: GPUFragmentState;
    primitive: GPUPrimitiveState;
    depthStencil?: GPUDepthStencilState;
}

// GPURenderPipeline - GPU 渲染管线
interface GPURenderPipeline {
    getBindGroupLayout(index: number): GPUBindGroupLayout;
}

interface GPUVertexState {
    module: GPUShaderModule;
    entryPoint: string;
    buffers?: GPUVertexBufferLayout[];
}

interface GPUVertexBufferLayout {
    arrayStride: number;
    stepMode: 'vertex' | 'instance';
    attributes: GPUVertexAttribute[];
}

interface GPUVertexAttribute {
    format: string;
    offset: number;
    shaderLocation: number;
}

interface GPUPrimitiveState {
    topology: 'point-list' | 'line-list' | 'triangle-list';
    pointSize?: number;
}

interface GPUDepthStencilState {
    depthWriteEnabled: boolean;
    depthCompare: string;
    format: string;
}

interface GPUFragmentState {
    module: GPUShaderModule;
    entryPoint: string;
    targets: GPUColorTargetState[];
}

interface GPUColorTargetState {
    format: string;
    blend?: GPUBlendState;
}

interface GPUBlendState {
    color: GPUBlendComponent;
    alpha: GPUBlendComponent;
}

interface GPUBlendComponent {
    srcFactor: string;
    dstFactor: string;
    operation: string;
}

interface GPUBindGroupDescriptor {
    layout: GPUBindGroupLayout;
    entries: GPUBindGroupEntry[];
}

interface GPUBindGroupEntry {
    binding: number;
    resource: { buffer: GPUBuffer };
}

interface GPUBindGroupLayout {
}

interface GPUBindGroup {
}

interface GPUPipelineLayout {
}

interface GPUCommandEncoder {
    beginRenderPass(descriptor: GPURenderPassDescriptor): GPURenderPassEncoder;
    finish(): GPUCommandBuffer;
}

interface GPURenderPassDescriptor {
    colorAttachments: GPURenderPassColorAttachment[];
}

interface GPURenderPassColorAttachment {
    view: GPUTextureView;
    clearValue?: GPUColor;
    loadOp: 'clear' | 'load';
    storeOp: 'store' | 'discard';
}

interface GPUColor {
    r: number;
    g: number;
    b: number;
    a: number;
}

interface GPURenderPassEncoder {
    setPipeline(pipeline: GPURenderPipeline): void;
    setBindGroup(index: number, bindGroup: GPUBindGroup): void;
    setVertexBuffer(slot: number, buffer: GPUBuffer, offset?: number, size?: number): void;
    draw(vertexCount: number, instanceCount?: number, firstVertex?: number, firstInstance?: number): void;
    end(): void;
}

interface GPUCommandBuffer {
}

interface GPUQueue {
    submit(commandBuffers: GPUCommandBuffer[]): void;
    writeBuffer(buffer: GPUBuffer, offset: number, data: BufferSource, srcOffset?: number, length?: number): void;
}

interface GPUCanvasContext {
    configure(descriptor: GPUCanvasConfiguration): void;
    getCurrentTexture(): GPUTexture;
    format: string;
}

interface GPUCanvasConfiguration {
    device: GPUDevice;
    format: GPUTextureFormat;
    alphaMode?: 'opaque' | 'premultiplied';
    usage?: number;
}

interface GPUTexture {
    createView(): GPUTextureView;
}

interface GPUTextureView {
}

type GPUTextureFormat = string;
