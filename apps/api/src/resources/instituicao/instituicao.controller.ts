import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  Delete,
  ParseUUIDPipe,
  Query,
} from '@nestjs/common';
import type { UUID } from "node:crypto";
import { InstituicaoService } from './instituicao.service';
import { CreateInstituicaoDto } from './dto/create-instituicao.dto';
import { UpdateInstituicaoDto } from './dto/update-instituicao.dto';
import { FindAllInstituicaoDto } from './dto/find-all-instituicao.dto';

@Controller('instituicao')
export class InstituicaoController {
  constructor(private readonly instituicaoService: InstituicaoService) {}

  @Post()
  create(@Body() createInstituicaoDto: CreateInstituicaoDto) {
    return this.instituicaoService.create(createInstituicaoDto);
  }

  @Get()
  findAll(@Query() query: FindAllInstituicaoDto) {
    return this.instituicaoService.findAll(query);
  }

  @Get(':id')
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.instituicaoService.findOne(id);
  }

  @Patch(':id')
  update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() updateInstituicaoDto: UpdateInstituicaoDto,
  ) {
    return this.instituicaoService.update(id, updateInstituicaoDto);
  }

  @Delete(':id')
  remove(@Param('id', ParseUUIDPipe) id: string) {
    return this.instituicaoService.remove(id);
  }
}
